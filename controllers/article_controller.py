import spacy
from flask import jsonify
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from stanza.server import CoreNLPClient
import os
from models.article import Article
from werkzeug.utils import secure_filename
from sentence_transformers import SentenceTransformer
from config.tripletsMapping import tripletsMapping

import threading

class ArticleController:
    def __init__(self):

        self.nlp = spacy.load("en_core_web_sm")

        self.es = Elasticsearch(
            "https://localhost:9200",
            basic_auth=("elastic", "SZoY=mikTz4MCctIcWhX"),
            ca_certs="/Users/varela/http_ca.crt"
        )

        self.model = SentenceTransformer('all-mpnet-base-v2')

        self.vector_lock = threading.Lock()


    def create_article(self, request):
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'})

        folder = request.form.get('folder', 'articles')
        folder_path = os.path.join('static', folder)

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if file:
            filename = os.path.join(
                folder_path, secure_filename(file.filename))

            file.save(filename)

            data = request.form.to_dict()
            article = Article(**data, path=folder)
            article.save()

            return jsonify({'message': 'Article created successfully', 'path': f'static/{folder}'})

    def get_article(self, article_id):
        article = Article.find_by_id(article_id)
        return jsonify(article.json())

    def update_article(self, request, article_id):
        data = request.get_json()
        article = Article.find_by_id(article_id)
        if article:
            article.update(data)
            return jsonify({'message': 'Updated article'})
        else:
            return jsonify({'message': 'Article not found'}, 404)

    def delete_article(self, article_id):
        article = Article.find_by_id(article_id)
        if article:
            article.delete()
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

        
    def extract_triplets(self, sentences):
        sentences_and_triplets = []

        with CoreNLPClient(annotators=["openie"], be_quiet=False, ) as client:
            for span in sentences:
                text = span.text if span.text else "Not Found"
                ann = client.annotate(text)
                triplet_sentence = []


                for sentence in ann.sentence:
                    for triple in sentence.openieTriple:

                        with self.vector_lock:
                            subject_vector = self.calculate_and_save_vector(triple.subject)
                            relation_vector = self.calculate_and_save_vector(triple.relation)
                            object_vector = self.calculate_and_save_vector(triple.object)
                        
                        triplet = {
                            'subject': {'text': triple.subject, 'vector':  subject_vector},
                            'relation': {'text': triple.relation, 'vector': relation_vector},
                            'object': {'text': triple.object, 'vector': object_vector},
                        }

                        
                        triplet_sentence.append(triplet)

                    if triplet_sentence:
                        sentences_and_triplets.append({
                            'sentence_text': text,
                            'triplets': triplet_sentence,
                        })

        return sentences_and_triplets
    
    def analyze_articles(self, request):
        try:
            result_collection = []
            should_clauses = []

            index_name = 'articles'

            query = {'bool': {'must': []}}

            search_params = request.args.to_dict()

            for key, value in search_params.items():
                if key == 'title':
                    query['bool']['must'].append({'term': {'title.keyword': value}})
                elif key in ['doi', 'issn', 'keys', 'pmc_id']:
                    values = [value] if not isinstance(value, list) else value
                    for single_value in values:
                        keywords = single_value.split(',')
                        for keyword in keywords:
                            should_clauses.append(
                                {'match': {f'{key}': keyword.strip()}})
                else:
                    query['bool']['must'].append({'match': {key: value}})

            if should_clauses:
                query['bool']['should'] = should_clauses
                query['bool']['minimum_should_match'] = 1

            if not self.es.indices.exists(index=index_name):
                        self.es.indices.create(index=index_name, mappings=tripletsMapping)

            response = self.es.search(index=index_name, body={'query': query})

            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                return jsonify({'error': f'Document not found in Elasticsearch'})

            for hit in hits:
                result = hit.get('_source', {})
                article_id = hit.get('_id', '')
                title = result.get('title', '')
                content = result.get('results', '')
                folder = result.get('path', '')
                
                doc = self.nlp(content)
                sentences_and_triplets = self.extract_triplets(doc.sents)

                response = {
                    'article_id': article_id,
                    'article_title': title,
                    'path': folder,
                    'data_analysis': sentences_and_triplets
                }

                
                index_name_triplets = 'triplets'
                
                try:
                    self.es.index(index=index_name_triplets, id=hit.get('_id'), body=response)
                except Exception as es_error:
                    print(f"Error indexing data into Elasticsearch: {es_error}")

                result_collection.append(response)

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

    def search(self, input_keyword):
        model = SentenceTransformer('all-mpnet-base-v2')
        vector_of_input_keyword = model.encode(input_keyword)

        query = {
            "field": "vector",
            "query_vector": vector_of_input_keyword,
            "k": 10,
            "num_candidates": 500
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
                        "title": result['_source']['title'],
                        "content": result['_source']['content']
                    }
                    json_results.append(json_result)
                except Exception as e:
                    print(e)

        return json_results
    
    def analyze_articles_with_semantic_search(self, query, request):
        query = request.args.get('query', '')

        if query:
            results = self.search(query)
            return jsonify({"results": results})
        else:
            return jsonify({"message": "Please provide a search query"})
