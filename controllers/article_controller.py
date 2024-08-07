import spacy
from flask import jsonify
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import os
from models.article import Article
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer
from config.tripletsMapping import tripletsMapping
import threading
from controllers.triplets_controller import TripletsController
from flask_jwt_extended import get_jwt_identity
from zipfile import ZipFile
from config.articleMapping import articleMapping
from metapub import PubMedFetcher

class ArticleController:
    def __init__(self):

        self.nlp = spacy.load("en_core_web_sm")

        elasticsearch_url = os.getenv("ELASTICSEARCH_URL")

        self.es = Elasticsearch(elasticsearch_url)

        self.model = SentenceTransformer('all-mpnet-base-v2')

        self.vector_lock = threading.Lock()

    def check_unique_pmc_id(self, pmc_id):

        result = self.es.search(index="articles", q=f"pmc_id:{pmc_id}")
        return result["hits"]["total"]["value"] == 0

    def create_article(self, request):
        main_folder = os.environ.get('MAIN_FOLDER', 'default_main_folder')

        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        current_user_id = get_jwt_identity()

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'})

        sub_folder = current_user_id
        folder_path = os.path.join('static', main_folder, sub_folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if file:
            filename = os.path.join(
                folder_path, secure_filename(file.filename))
            file.save(filename)

            data = request.form.to_dict()

            if not self.es.indices.exists(index='articles'):
                self.es.indices.create(
                    index='articles', mappings=articleMapping)

            if self.check_unique_pmc_id(data.get('pmc_id')):
                article = Article(
                    **data, vector=[], path=current_user_id)
                article.save()
            else:
                return jsonify({'error': 'Article already exists'}), 409

            return jsonify({'message': 'Article created successfully', 'path': f'static/{main_folder}/{sub_folder}'})

    def get_article(self, article_id):
        article = Article.find_by_id(article_id)
        return jsonify(article.json())

    def update_article(self, request, article_id):
        data = request.form.to_dict()
        article = Article.find_by_id(article_id)
        if article:
            article.update(data, article_id)
            return jsonify({'message': 'Updated article'})
        else:
            return jsonify({'message': 'Article not found'}, 404)

    def delete_article(self, article_id):
        article = Article.find_by_id(article_id)
        if article:
            article.delete(article_id)
            return jsonify({'message': 'Article removed'})
        else:
            return jsonify({'message': 'Article not found'}, 404)
    
    def exampleMessage(self):
        return jsonify({'message': 'Hola no necesito el token'})

    def search_articles(self, request):
        query = request.args.get('query')
        articles = Article.search(query)
        return jsonify([article.json() for article in articles])
    
    def read_file_with_encodings(self, file_path):
        encodings = ['utf-8', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError(
            f"Cannot decode file {file_path} with available encodings.")

    def calculate_and_save_vector(self, text):
        try:
            if not text:
                return None
            vector = self.model.encode(text)
            vector_list = vector.tolist()
            return vector_list
        except Exception as e:
            print(f"Error in calculate_and_save_vector: {e}")
            return None

    def analyze_all_articles(self, request):
        try:
            index_name = 'articles'
            index_name_triplets = 'triplets'

            search_params = request.args.to_dict()

            threads = search_params.get('threads')
            memory = search_params.get('memory')

            if not self.es.indices.exists(index=index_name_triplets):
                self.es.indices.create(
                    index=index_name_triplets, mappings=tripletsMapping)

            response = self.es.search(index=index_name, body={
                'query': {'match_all': {}}, 'size': 1000})

            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                print('No documents found in Elasticsearch')
                return jsonify({'error': 'No documents found in Elasticsearch'})

            result_collection = []
            total_articles = len(hits)

            for index, hit in enumerate(hits):
                result = hit.get('_source', {})
                article_id, title, content, folder, pmc_id = hit.get('_id', ''), result.get('title', ''), result.get('content', ''), result.get('path', ''), result.get('pmc_id', '')

                doc = self.nlp(content)
                
                sentences_and_triplets = TripletsController.extract_triplets(self, doc.sents, memory, threads)


                response = {
                            'article_id': article_id, 
                            'article_title': title,
                            'path': folder, 
                            'data_analysis': sentences_and_triplets,
                            'pmc_id': pmc_id,
                            }
                
                result_collection.append(response)


               

            TripletsController.post_triplets_with_vectors(self, result_collection)

            

            return jsonify({'message': 'Analysis completed successfully for all articles'})
        
        except Exception as error:
            print(f"Error during analysis: {error}")
            return jsonify({'error': 'An error occurred during analysis'})
        
    def get_article_info(self, pmc_number):
        fetch = PubMedFetcher()
        try:
            article = fetch.article_by_pmcid(pmc_number)
            if article:
                return {
                    "pmc_id": pmc_number,
                    "title": getattr(article, 'title', ''),
                    "authors": getattr(article, 'authors', ''),
                    "journal": getattr(article, 'journal', ''),
                    "abstract": getattr(article, 'abstract', ''),
                    "doi": getattr(article, 'doi', ''),
                    "issn": getattr(article, 'issn', ''),
                    "year": getattr(article, 'year', ''),
                    "volume": getattr(article, 'volume', ''),
                    "issue": getattr(article, 'issue', ''),
                    "pages": getattr(article, 'pages', ''),
                    "url": getattr(article, 'url', '')
                }
        except Exception as e:
            print(
                f"Error al obtener información del artículo {pmc_number}: {str(e)}")
        return None
        
    def analyze_articles(self, request):
        try:
            result_collection = []
            should_clauses = []

            index_name = 'articles'
            index_name_triplets = 'triplets'

            query = {'bool': {'must': []}}

            search_params = request.args.to_dict()

            threads = search_params.get('threads')
            memory = search_params.get('memory')

            for key, value in search_params.items():
                if key in ['threads', 'memory']:
                    continue
                else:
                    query['bool']['must'].append({'match': {key: value}})

            if should_clauses:
                query['bool']['should'] = should_clauses
                query['bool']['minimum_should_match'] = 1

            if not self.es.indices.exists(index=index_name_triplets):
                self.es.indices.create(
                    index=index_name_triplets, mappings=tripletsMapping)

            response = self.es.search(index=index_name, body={'query': query})

            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                return jsonify({'error': f'Document not found in Elasticsearch'}), 404

            first_hit = hits[0]
            result = first_hit.get('_source', {})
            article_id = first_hit.get('_id', '')
            title = result.get('title', '')
            folder = result.get('path', '')

            triplets_query = {
                'bool': {
                    'must': [{'match': {'article_id': article_id}}]
                }
            }

            triplets_response = self.es.search(
                index=index_name_triplets, body={'query': triplets_query})
            triplets_hits = triplets_response.get('hits', {}).get('hits', [])

            if triplets_hits:
                # Triplets found, return JSON response immediately
                triplets_data = [triplet['_source']
                                 for triplet in triplets_hits]
                for triplet in triplets_data:
                    triplet['data_analysis'] = [
                        {"sentence_text": analysis["sentence_text"], "triplets": analysis["triplets"]} for analysis in triplet.get("data_analysis", [])

                    ]
                return jsonify({
                    'article_id': article_id,
                    'article_title': title,
                    'path': folder,
                    'existing_triplets': triplets_data
                })

            for hit in hits:
                result = hit.get('_source', {})
                article_id = hit.get('_id', '')
                title = result.get('title', '')
                content = result.get('content', '')
                folder = result.get('path', '')
                pmc_id = result.get('pmc_id', '')


                doc = self.nlp(content)
                sentences_and_triplets = TripletsController.extract_triplets(
                    self, doc.sents, memory, threads)

                response = {
                    'article_id': article_id,
                    'article_title': title,
                    'path': folder,
                    'data_analysis': sentences_and_triplets,
                    'pmc_id': pmc_id,
                }

                result_collection.append(response)

            TripletsController.post_triplets_with_vectors(
                self, result_collection)

            for item in result_collection:
                for analysis_item in item['data_analysis']:
                    analysis_item.pop('sentence_text_vector', None)

            return jsonify(result_collection)

        except NotFoundError:
            return jsonify({'error': f'Document not found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during analysis: {str(e)}'})

    def analyze_my_articles(self, request):
        try:
            result_collection = []

            index_name = 'articles'
            index_name_triplets = 'triplets'

            search_params = request.args.to_dict()

            threads = search_params.get('threads')
            memory = search_params.get('memory')

            if not self.es.indices.exists(index=index_name_triplets):
                self.es.indices.create(
                    index=index_name_triplets, mappings=tripletsMapping)

            current_user_id = get_jwt_identity()

            response = self.es.search(index=index_name, body={
                'query': {
                    'bool': {
                        'must': [
                            {'match': {'path': current_user_id}}
                        ]
                    }
                }
            })

            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                return jsonify({'error': f'Document not found in Elasticsearch'})

            first_hit = hits[0]
            result = first_hit.get('_source', {})
            article_id = first_hit.get('_id', '')
            title = result.get('title', '')
            folder = result.get('path', '')

            triplets_query = {
                'bool': {
                    'must': [{'match': {'article_id': article_id}}]
                }
            }

            triplets_response = self.es.search(
                index=index_name_triplets, body={'query': triplets_query})
            triplets_hits = triplets_response.get('hits', {}).get('hits', [])

            if triplets_hits:
                # Triplets found, return JSON response immediately
                triplets_data = [triplet['_source']
                                 for triplet in triplets_hits]
                for triplet in triplets_data:
                    triplet['data_analysis'] = [
                        {"sentence_text": analysis["sentence_text"], "triplets": analysis["triplets"]} for analysis in triplet.get("data_analysis", [])

                    ]
                return jsonify({
                    'article_id': article_id,
                    'article_title': title,
                    'path': folder,
                    'existing_triplets': triplets_data
                })

            for hit in hits:
                result = hit.get('_source', {})
                article_id = hit.get('_id', '')
                title = result.get('title', '')
                content = result.get('content', '')
                folder = result.get('path', '')
                pmc_id = result.get('pmc_id', '')

                doc = self.nlp(content)
                sentences_and_triplets = TripletsController.extract_triplets(
                    self, doc.sents, memory, threads)

                response = {
                    'article_id': article_id,
                    'pmc_id': pmc_id,
                    'article_title': title,
                    'path': folder,
                    'data_analysis': sentences_and_triplets
                }

                result_collection.append(response)

            TripletsController.post_triplets_with_vectors(
                self, result_collection)

            for item in result_collection:
                for analysis_item in item['data_analysis']:
                    analysis_item.pop('sentence_text_vector', None)

            return jsonify(result_collection)

        except NotFoundError:
            return jsonify({'error': f'Document not found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during analysis: {str(e)}'})

    def get_all_articles(self):
        try:
            index_name = 'articles'
            response = self.es.search(index=index_name, body={
                'query': {
                    'match_all': {}
                }
            })

            articles = response.get('hits', {}).get('hits', [])

            if not articles:
                return jsonify({'error': 'No articles found in Elasticsearch'})

            result_collection = []

            for article in articles:
                result = article.get('_source', {})
                article_id = article.get('_id', '')
                title = result.get('title', '')
                authors = result.get('authors', '')
                journal = result.get('journal', '')
                abstract = result.get('abstract', '')
                doi = result.get('doi', '')
                issn = result.get('issn', '')
                year = result.get('year', '')
                volume = result.get('volume', '')
                issue = result.get('issue', '')
                pages = result.get('pages', '')
                url = result.get('url', '')
                pmc_id = result.get('pmc_id', '')
                content = result.get('content', '')
                path = result.get('path', '')

                result_collection.append({
                    "article_id": article_id,
                    "title": title,
                    "authors": authors,
                    "journal": journal,
                    "abstract": abstract,
                    "doi": doi,
                    "issn": issn,
                    "year": year,
                    "volume": volume,
                    "issue": issue,
                    "pages": pages,
                    "url": url,
                    "pmc_id": pmc_id,
                    "content": content,
                    "path": path,
                })

            return jsonify(result_collection)

        except NotFoundError:
            return jsonify({'error': 'No articles found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'})

    def get_my_articles(self):
        try:

            current_user_id = get_jwt_identity()

            index_name = 'articles'

            response = self.es.search(index=index_name, body={
                'query': {
                    'bool': {
                        'must': [
                            {'match': {'path': current_user_id}}
                        ]
                    }
                }
            })

            articles = response.get('hits', {}).get('hits', [])

            if not articles:
                return jsonify({'error': 'No articles found in Elasticsearch'})

            result_collection = []

            for article in articles:
                result = article.get('_source', {})
                article_id = article.get('_id', '')
                title = result.get('title', '')
                authors = result.get('authors', '')
                journal = result.get('journal', '')
                issn = result.get('issn', '')
                doi = result.get('doi', '')
                pmc_id = result.get('pmc_id', '')
                keys = result.get('keys', '')
                abstract = result.get('abstract', '')
                objectives = result.get('objectives', '')
                content = result.get('content', '')
                methods = result.get('methods', '')
                results = result.get('results', '')
                conclusion = result.get('conclusion', '')
                path = result.get('path', '')

                result_collection.append({
                    'id': article_id,
                    'doi': doi,
                    'path': path,
                    'issn': issn,
                    'title': title,
                    'content': content,
                    'authors': authors,
                    'journal': journal,
                    'pmc_id': pmc_id,
                    'keys': keys,
                    'abstract': abstract,
                    'objectives': objectives,
                    'methods': methods,
                    'results': results,
                    'conclusion': conclusion
                })

            return jsonify(result_collection)

        except NotFoundError:
            return jsonify({'error': 'No articles found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'})

    def search(self, input_keyword, top_k, candidates):
        model = SentenceTransformer('all-mpnet-base-v2')
        vector_of_input_keyword = model.encode(input_keyword)

        query = {
            "field": "vector",
            "query_vector": vector_of_input_keyword,
            "k": top_k,
            "num_candidates": candidates
        }
        res = self.es.knn_search(
            index="articles",
            knn=query,
            source=["title", "authors", "journal", "abstract", "doi", "issn", "year", "url", "pmc_id"])
        results = res["hits"]["hits"]

        # Convert results to JSON format
        json_results = []
        for result in results:
            if '_source' in result:
                try:
                    json_result = {
                        "id_article": result['_id'],
                        "title": result['_source']['title'],
                        "authors": result['_source']['authors'],
                        "journal": result['_source']['journal'],
                        "abstract": result['_source']['abstract'],
                        "doi": result['_source']['doi'],
                        "issn": result['_source']['issn'],
                        "year": result['_source']['year'],
                        "url": result['_source']['url'],
                        "pmc_id": result['_source']['pmc_id'],
                    }
                    json_results.append(json_result)
                except Exception as e:
                    print(e)

        return json_results

    def search_articles_with_semantic_search(self, candidates, top_k, query, request):
        query = request.args.get('query', '')

        if query:
            results = self.search(query, top_k, candidates)
            return jsonify({"results": results})
        else:
            return jsonify({"message": "Please provide a search query"})

    def create_articles_from_json(self, json_data):
        articles = []

        for item in json_data:
            article = Article(**item)
            articles.append(article)
            article.save()

        return articles

    def extract_zip(self, zip_path, extract_path):
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        os.remove(zip_path)

    def post_articles_in_zip(self, request):
        main_folder = os.environ.get('MAIN_FOLDER', 'default_main_folder')

        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        current_user_id = get_jwt_identity()

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'})

        sub_folder = current_user_id
        folder_path = os.path.join('static', main_folder, sub_folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if file:
            zip_filename = os.path.join(
                folder_path, secure_filename(file.filename))
            file.save(zip_filename)

            # Extraer el archivo zip en la misma carpeta
            self.extract_zip(zip_filename, folder_path)

        articles = []

        def check_unique_pmc_id(pmc_id):
            result = self.es.search(index="articles", q=f"pmc_id:{pmc_id}")
            return result["hits"]["total"]["value"] == 0

        for filename in os.listdir(folder_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(folder_path, filename)
                try:
                    content = self.read_file_with_encodings(file_path)
                    pmc_id = os.path.splitext(filename)[0]
                    pmc_number = pmc_id.replace("PMC", "")

                    article_info = self.get_article_info(pmc_number)

                    if article_info is not None:
                        vector = self.calculate_and_save_vector(
                            article_info['abstract'])
                        article_data = {
                            "title": article_info['title'],
                            "authors": article_info['authors'],
                            "journal": article_info['journal'],
                            "abstract": article_info['abstract'],
                            "doi": article_info['doi'],
                            "issn": article_info['issn'],
                            "year": article_info['year'],
                            "volume": article_info['volume'],
                            "issue": article_info['issue'],
                            "pages": article_info['pages'],
                            "url": article_info['url'],
                            "pmc_id": article_info['pmc_id'],
                            "content": content,
                            "path": sub_folder,
                            "vector": vector
                        }

                        try:
                            if not self.es.indices.exists(index='articles'):
                                self.es.indices.create(
                                    index='articles', mappings=articleMapping)
                                
                            if check_unique_pmc_id(pmc_number):
                                self.es.index(index='articles', document=article_data)
                                articles.append(article_data)
                            else:
                                print(f"El artículo {pmc_number} ya existe en Elasticsearch.")
                        except Exception as e:
                            print(
                                f"Error al enviar datos a Elasticsearch: {str(e)}")
                except UnicodeDecodeError as e:
                    print(f"Error al leer archivo {file_path}: {str(e)}")
                except Exception as e:
                    print(f"Error al procesar archivo {file_path}: {str(e)}")
                    continue

        self.create_articles_from_json(articles)

        return jsonify({'articles': articles})
    
    def post_articles_in_folder(self, folder):
        main_folder = os.environ.get('MAIN_FOLDER')
        folder_path = os.path.join('static', main_folder, folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        

        articles = []

        def check_unique_pmc_id(pmc_id):
            result = self.es.search(index="articles", q=f"pmc_id:{pmc_id}")
            return result["hits"]["total"]["value"] == 0

        for filename in os.listdir(folder_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(folder_path, filename)
                try:
                    content = self.read_file_with_encodings(file_path)
                    pmc_id = os.path.splitext(filename)[0]
                    pmc_number = pmc_id.replace("PMC", "")

                    article_info = self.get_article_info(pmc_number)

                    if article_info is not None:
                        vector = self.calculate_and_save_vector(
                            article_info['abstract'])
                        article_data = {
                            "title": article_info['title'],
                            "authors": article_info['authors'],
                            "journal": article_info['journal'],
                            "abstract": article_info['abstract'],
                            "doi": article_info['doi'],
                            "issn": article_info['issn'],
                            "year": article_info['year'],
                            "volume": article_info['volume'],
                            "issue": article_info['issue'],
                            "pages": article_info['pages'],
                            "url": article_info['url'],
                            "pmc_id": article_info['pmc_id'],
                            "content": content,
                            "path": folder,
                            "vector": vector
                        }

                        try:
                            if not self.es.indices.exists(index='articles'):
                                self.es.indices.create(
                                    index='articles', mappings=articleMapping)
                                
                            if check_unique_pmc_id(pmc_number):
                                self.es.index(index='articles', document=article_data)
                                articles.append(article_data)
                            else:
                                print(f"El artículo {pmc_number} ya existe en Elasticsearch.")
                        except Exception as e:
                            print(
                                f"Error al enviar datos a Elasticsearch: {str(e)}")
                except UnicodeDecodeError as e:
                    print(f"Error al leer archivo {file_path}: {str(e)}")
                except Exception as e:
                    print(f"Error al procesar archivo {file_path}: {str(e)}")
                    continue

        self.create_articles_from_json(articles)

        return jsonify({'articles': articles})

