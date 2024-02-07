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
from flask_jwt_extended import  get_jwt_identity
from zipfile import ZipFile

class ArticleController:
    def __init__(self):

        self.nlp = spacy.load("en_core_web_sm")

        elasticsearch_url = os.getenv("ELASTICSEARCH_URL")

        self.es = Elasticsearch(elasticsearch_url)

        self.model = SentenceTransformer('all-mpnet-base-v2')

        self.vector_lock = threading.Lock()

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
            article = Article(
                **data, vector=[], path=current_user_id)
            article.save()

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

    def search_articles(self, request):
        query = request.args.get('query')
        articles = Article.search(query)
        return jsonify([article.json() for article in articles])

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
                self.es.indices.create(index=index_name_triplets, mappings=tripletsMapping)

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
                article_id, title, content, folder = hit.get('_id', ''), result.get(
                    'title', ''), result.get('results', ''), result.get('path', '')

                doc = self.nlp(content)
                sentences_and_triplets = TripletsController.extract_triplets(
                    self, doc.sents, memory, threads)

                response = {'article_id': article_id, 'article_title': title,
                            'path': folder, 'data_analysis': sentences_and_triplets}

                try:
                    self.es.index(index=index_name_triplets, body=response)
                except Exception as es_error:
                    print(
                        f"Error indexing data into Elasticsearch: {es_error}")

                result_collection.append(response)

                print(f"Analyzed article {index + 1} of {total_articles}")

            TripletsController.post_triplets_with_vectors(
                self, result_collection)

            print("Analysis completed successfully for all articles")

            return jsonify({'message': 'Analysis completed successfully for all articles'})

        except Exception as error:
            print(f"Error during analysis: {error}")
            return jsonify({'error': 'An error occurred during analysis'})

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
                content = result.get('results', '')
                folder = result.get('path', '')

                doc = self.nlp(content)
                sentences_and_triplets = TripletsController.extract_triplets(
                    self, doc.sents, memory, threads)

                response = {
                    'article_id': article_id,
                    'article_title': title,
                    'path': folder,
                    'data_analysis': sentences_and_triplets
                }

                try:
                    self.es.index(index=index_name_triplets, body=response)
                except Exception as es_error:
                    print(
                        f"Error indexing data into Elasticsearch: {es_error}")

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


            response= self.es.search(index=index_name, body={
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
                content = result.get('results', '')
                folder = result.get('path', '')

                doc = self.nlp(content)
                sentences_and_triplets = TripletsController.extract_triplets(
                    self, doc.sents, memory, threads)

                response = {
                    'article_id': article_id,
                    'article_title': title,
                    'path': folder,
                    'data_analysis': sentences_and_triplets
                }

                try:
                    self.es.index(index=index_name_triplets, body=response)
                except Exception as es_error:
                    print(
                        f"Error indexing data into Elasticsearch: {es_error}")

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
        
    def get_my_articles(self):
        try:

            current_user_id = get_jwt_identity()

            index_name = 'articles'

            response= self.es.search(index=index_name, body={
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
        res = self.es.knn_search(index="articles",
                                 knn=query,
                                 source=["title", "content"])
        results = res["hits"]["hits"]

        # Convert results to JSON format
        json_results = []
        for result in results:
            if '_source' in result:
                try:
                    json_result = {
                        "id_article": result['_id'],
                        "title": result['_source']['title'],
                        "content": result['_source']['content']
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
            zip_filename = os.path.join(folder_path, secure_filename(file.filename))
            file.save(zip_filename)

            # Extraer el archivo zip en la misma carpeta
            self.extract_zip(zip_filename, folder_path)


        articles = []
        for filename in os.listdir(folder_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                    lines = content.splitlines()

                    # Logic to extract the title
                    title_line_index = next(
                        (index for index, line in enumerate(lines) if line.strip().lower().startswith("article")), None)

                    title = None
                    if title_line_index is not None and title_line_index + 1 < len(lines):
                        title = lines[title_line_index + 1].strip()

                    results_start = content.find("Results")
                    discussion_start = content.find("Discussion")
                    methods_start = content.find("Methods")
                    abstract_start = content.find("Instroduction")

                    # Logic to extract the methods
                    methods = None
                    if methods_start != -1 and results_start != -1:

                        methods_line_end = content.find('\n', methods_start)

                        methods_block = content[methods_line_end +
                                                1:results_start].strip()

                        methods_lines = [
                            line for line in methods_block.splitlines() if line.strip()]

                        methods = methods_lines

                    # Logic to extract the abstract
                    abstract = None
                    if abstract_start != -1 and methods_start != -1:

                        abstract_line_end = content.find('\n', abstract_start)

                        abstract_block = content[abstract_line_end +
                                                 1:methods_start].strip()

                        abstract_lines = [
                            line for line in abstract_block.splitlines() if line.strip()]

                        abstract = abstract_lines

                    # Logic to extract the results
                    results = None
                    if results_start != -1 and discussion_start != -1:

                        results_line_end = content.find('\n', results_start)

                        results_block = content[results_line_end +
                                                1:discussion_start].strip()

                        results_lines = [
                            line for line in results_block.splitlines() if line.strip()]

                        results = results_lines

                pmc_id = os.path.splitext(filename)[0]

                abstract = abstract if abstract is not None else ''
                methods = methods if methods is not None else ''
                results = results if results is not None else ''

                if isinstance(abstract, list):
                    abstract = ' '.join(map(str, abstract))
                if isinstance(methods, list):
                    methods = ' '.join(map(str, methods))
                if isinstance(results, list):
                    results = ' '.join(map(str, results))

                concatenate_content = (abstract or '') + \
                    (methods or '') + (results or '')

                article = Article(
                    title=title,
                    authors=None,
                    journal=None,
                    issn=None,
                    doi=None,
                    pmc_id=pmc_id,
                    keys=None,
                    abstract=abstract,
                    objectives=None,
                    content=content,
                    methods=methods,
                    results=results,
                    conclusion=None,
                    path=current_user_id,
                    vector=[]
                )

                articles.append(article.json())

        self.create_articles_from_json(articles)

        return jsonify({'articles': articles})
    
    def post_articles_in_folder(self, folder):
        main_folder = os.environ.get('MAIN_FOLDER', 'default_main_folder')

        folder_path = os.path.join('static', main_folder, folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)


        articles = []
        for filename in os.listdir(folder_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(folder_path, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                    lines = content.splitlines()

                    # Logic to extract the title
                    title_line_index = next(
                        (index for index, line in enumerate(lines) if line.strip().lower().startswith("article")), None)

                    title = None
                    if title_line_index is not None and title_line_index + 1 < len(lines):
                        title = lines[title_line_index + 1].strip()

                    results_start = content.find("Results")
                    discussion_start = content.find("Discussion")
                    methods_start = content.find("Methods")
                    abstract_start = content.find("Instroduction")

                    # Logic to extract the methods
                    methods = None
                    if methods_start != -1 and results_start != -1:

                        methods_line_end = content.find('\n', methods_start)

                        methods_block = content[methods_line_end +
                                                1:results_start].strip()

                        methods_lines = [
                            line for line in methods_block.splitlines() if line.strip()]

                        methods = methods_lines

                    # Logic to extract the abstract
                    abstract = None
                    if abstract_start != -1 and methods_start != -1:

                        abstract_line_end = content.find('\n', abstract_start)

                        abstract_block = content[abstract_line_end +
                                                 1:methods_start].strip()

                        abstract_lines = [
                            line for line in abstract_block.splitlines() if line.strip()]

                        abstract = abstract_lines

                    # Logic to extract the results
                    results = None
                    if results_start != -1 and discussion_start != -1:

                        results_line_end = content.find('\n', results_start)

                        results_block = content[results_line_end +
                                                1:discussion_start].strip()

                        results_lines = [
                            line for line in results_block.splitlines() if line.strip()]

                        results = results_lines

                pmc_id = os.path.splitext(filename)[0]

                abstract = abstract if abstract is not None else ''
                methods = methods if methods is not None else ''
                results = results if results is not None else ''

                if isinstance(abstract, list):
                    abstract = ' '.join(map(str, abstract))
                if isinstance(methods, list):
                    methods = ' '.join(map(str, methods))
                if isinstance(results, list):
                    results = ' '.join(map(str, results))

                concatenate_content = (abstract or '') + \
                    (methods or '') + (results or '')

                article = Article(
                    title=title,
                    authors=None,
                    journal=None,
                    issn=None,
                    doi=None,
                    pmc_id=pmc_id,
                    keys=None,
                    abstract=abstract,
                    objectives=None,
                    content=content,
                    methods=methods,
                    results=results,
                    conclusion=None,
                    path=folder,
                    vector=[]
                )

                articles.append(article.json())

        self.create_articles_from_json(articles)

        return jsonify({'articles': articles})
