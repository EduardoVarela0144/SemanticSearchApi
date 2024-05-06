import spacy
from flask import jsonify, make_response
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from stanza.server import CoreNLPClient
import os
from sentence_transformers import SentenceTransformer
from config.tripletsMapping import tripletsMapping
import threading
import pandas as pd
from io import StringIO
from flask_jwt_extended import get_jwt_identity

import torch
from torch.utils.data import Dataset, DataLoader


class TripletsController:
    def __init__(self):

        self.nlp = spacy.load("en_core_web_sm")

        elasticsearch_url = os.getenv("ELASTICSEARCH_URL")

        self.es = Elasticsearch(elasticsearch_url)

        self.model = SentenceTransformer('all-mpnet-base-v2')

        self.vector_lock = threading.Lock()

    def search_triplets(self, input_keyword, top_k, candidates):
        model = SentenceTransformer('all-mpnet-base-v2')
        vector_of_input_keyword = model.encode(input_keyword)

        query = {
            "field": "sentence_text_vector",
            "query_vector": vector_of_input_keyword,
            "k": top_k,
            "num_candidates": candidates
        }

        res = self.es.knn_search(
            index="triplets",
            knn=query,
            source=["article_id", "sentence_text", "triplets"]
        )

        results = res["hits"]["hits"]

        json_results = []
        for result in results:
            if '_source' in result:
                try:
                    json_result = {
                        "article_id": result['_source']['article_id'],
                        "sentence_text": result['_source']['sentence_text'],
                        "triplets": result['_source']['triplets']
                    }
                    json_results.append(json_result)
                except Exception as e:
                    print("Error", e)

        return json_results

    def search_triplets_with_semantic_search(self, candidates, top_k, query, request):
        query = request.args.get('query', '')

        if query:
            results = self.search_triplets(query, top_k, candidates)
            return jsonify({"results": results})
        else:
            return jsonify({"message": "Please provide a search query"})

    def extract_triplets(self, sentences, memory, threads):
        sentences_and_triplets = []

        with CoreNLPClient(annotators=["openie"], be_quiet=False, max_mem=memory, threads=threads) as client:
            for span in sentences:
                text = span.text if span.text else "Not Found"
                ann = client.annotate(text)
                triplet_sentence = []

                for sentence in ann.sentence:
                    for triple in sentence.openieTriple:

                        triplet = {
                            'subject': {'text': triple.subject},
                            'relation': {'text': triple.relation},
                            'object': {'text': triple.object},
                        }

                        triplet_sentence.append(triplet)

                    if triplet_sentence:
                        sentences_and_triplets.append({
                            'sentence_text': text,
                            'sentence_text_vector': self.calculate_and_save_vector(text),
                            'triplets': triplet_sentence,
                        })

        return sentences_and_triplets

    def post_triplets_with_vectors(self, result_collection):
        index_name_triplets_vector = 'triplets'

        if not self.es.indices.exists(index=index_name_triplets_vector):
            self.es.indices.create(
                index=index_name_triplets_vector, mappings=tripletsMapping)

        for result in result_collection:
            article_id = result.get('article_id')
            path = result.get('path')
            data_analysis_list = result.get('data_analysis', [])

            try:
                for data_analysis in data_analysis_list:
                    sentence_text_vector = data_analysis.get(
                        'sentence_text_vector')
                    sentence_text = data_analysis.get('sentence_text')
                    triplets = data_analysis.get('triplets')

                    if all([article_id, sentence_text_vector, sentence_text]):
                        triplet_vector_data = {
                            'article_id': article_id,
                            'sentence_text_vector': sentence_text_vector,
                            'sentence_text': sentence_text,
                            'triplets': triplets,
                            'path' : path
                        }

                        try:
                            self.es.index(
                                index=index_name_triplets_vector, body=triplet_vector_data)
                            print("Indexed successfully.")
                        except Exception as es_error:
                            print(
                                f"Error indexing triplet vector data into Elasticsearch: {es_error}")
                    else:
                        print(
                            "Skipping data analysis due to missing values:", data_analysis)
            except Exception as result_error:
                print(f"Error processing result: {result_error}")

    def get_all_triplets(self):
        try:
            index_name = 'triplets'
            response = self.es.search(index=index_name, body={
                'query': {
                    'match_all': {}
                }
            })

            triplets = response.get('hits', {}).get('hits', [])

            if not triplets:
                return jsonify({'error': 'No triplets found in Elasticsearch'})

            result_collection = []

            for triplet in triplets:
                result = triplet.get('_source', {})
                triplet_id = triplet.get('_id', '')
                article_id = result.get('article_id', '')
                triplets = result.get('triplets', [])

                result_collection.append({
                    'id': triplet_id,
                    'article_id': article_id,
                    'triplets': triplets,
                })

            return jsonify(result_collection)

        except NotFoundError:
            return jsonify({'error': 'No articles found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'})
        

    def get_triplets_data_set(self, request, page_number, page_size):
        try:
            index_name = 'triplets'

            # Parámetros de paginación
            page_number = int(page_number)
            page_size = int(page_size)

            # Calcular el índice de inicio y fin para la paginación
            start_index = (page_number - 1) * page_size

            response = self.es.search(index=index_name, body={
                'query': {
                    'match_all': {}
                }
            })

            triplets = response.get('hits', {}).get('hits', [])

            if not triplets:
                return jsonify({'error': 'No triplets found in Elasticsearch'})

            result_collection = []

            for triplet in triplets:
                result = triplet.get('_source', {})
                triplet_id = triplet.get('_id', '')
                article_id = result.get('article_id', '')
                triplets = result.get('triplets', [])

                result_collection.append({
                    'id': triplet_id,
                    'article_id': article_id,
                    'triplets': triplets,
                })

            # Obtener el número total de triplets desde Elasticsearch
            total_triplets = response.get('hits', {}).get(
                'total', {}).get('value', 0)

            # Calcular información de paginación
            total_pages = (total_triplets + page_size - 1) // page_size
            current_page = page_number

            pagination_info = {
                'total_triplets': total_triplets,
                'total_pages': total_pages,
                'current_page': current_page
            }

            return jsonify({'result_collection': result_collection, 'pagination_info': pagination_info})

        except NotFoundError:
            return jsonify({'error': 'No articles found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'})
       
        
    def get_my_triplets(self, request, page_number, page_size):
        try:
            current_user_id = get_jwt_identity()
            index_name = 'triplets'

            # Parámetros de paginación
            page_number = int(page_number)
            page_size = int(page_size)

            # Calcular el índice de inicio y fin para la paginación
            start_index = (page_number - 1) * page_size

            response = self.es.search(index=index_name, body={
                'query': {
                    'bool': {
                        'must': [
                            {'match': {'path': current_user_id}}
                        ]
                    }
                },
                'from': start_index,
                'size': page_size
            })

           
            triplets = response.get('hits', {}).get('hits', [])

            if not triplets:
                return jsonify({'error': 'No triplets found in Elasticsearch'})

            result_collection = []

            for triplet in triplets:
                result = triplet.get('_source', {})
                triplet_id = triplet.get('_id', '')
                article_id = result.get('article_id', '')
                triplets = result.get('triplets', [])

                result_collection.append({
                    'id': triplet_id,
                    'article_id': article_id,
                    'triplets': triplets,
                })

            # Obtener el número total de triplets desde Elasticsearch
            total_triplets = response.get('hits', {}).get(
                'total', {}).get('value', 0)

            # Calcular información de paginación
            total_pages = (total_triplets + page_size - 1) // page_size
            current_page = page_number

            pagination_info = {
                'total_triplets': total_triplets,
                'total_pages': total_pages,
                'current_page': current_page
            }

            return jsonify({'result_collection': result_collection, 'pagination_info': pagination_info})

        except NotFoundError:
            return jsonify({'error': 'No articles found in Elasticsearch'})

        except Exception as e:
            return jsonify({'error': f'Error during search: {str(e)}'})

    def export_triplets_to_csv(self, request=None):
        index_name_triplets = 'triplets'

        try:
            es_data = self.es.search(index=index_name_triplets, size=10000)

            triplets_data = es_data['hits']['hits']

            triplets_list = []

            for triplet_data in triplets_data:
                triplet_source = triplet_data.get('_source', {})
                article_id = triplet_source.get('article_id', '')
                triplets = triplet_source.get('triplets', [])

                for triplet in triplets:
                    subject_text = triplet.get('subject', {}).get('text', '')
                    relation_text = triplet.get('relation', {}).get('text', '')
                    object_text = triplet.get('object', {}).get('text', '')

                    flattened_triplet = {
                        'article_id': article_id,
                        'subject_text': subject_text,
                        'relation_text': relation_text,
                        'object_text': object_text
                    }

                    triplets_list.append(flattened_triplet)

            df_triplets = pd.DataFrame(triplets_list)

            csv_content = StringIO()
            df_triplets.to_csv(csv_content, index=False)

            response = make_response(csv_content.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=triplets.csv'

            print("Triplet data exported to CSV")

            return response

        except Exception as es_error:
            print(f"Error retrieving triplet data from Elasticsearch: {es_error}")
            return make_response("Error retrieving triplet data", 500)
        
    def export_my_triplets_to_csv(self, request=None):
        index_name_triplets = 'triplets'

        try:
            current_user_id = get_jwt_identity()

            es_data = self.es.search(index=index_name_triplets, body={
                'query': {
                    'bool': {
                        'must': [
                            {'match': {'path': current_user_id}}
                        ]
                    }
                }
            })

            triplets_data = es_data['hits']['hits']

            triplets_list = []

            for triplet_data in triplets_data:
                triplet_source = triplet_data.get('_source', {})
                article_id = triplet_source.get('article_id', '')
                triplets = triplet_source.get('triplets', [])

                for triplet in triplets:
                    subject_text = triplet.get('subject', {}).get('text', '')
                    relation_text = triplet.get('relation', {}).get('text', '')
                    object_text = triplet.get('object', {}).get('text', '')

                    flattened_triplet = {
                        'article_id': article_id,
                        'subject_text': subject_text,
                        'relation_text': relation_text,
                        'object_text': object_text
                    }

                    triplets_list.append(flattened_triplet)

            df_triplets = pd.DataFrame(triplets_list)

            csv_content = StringIO()
            df_triplets.to_csv(csv_content, index=False)

            response = make_response(csv_content.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=triplets.csv'

            print("Triplet data exported to CSV")

            return response

        except Exception as es_error:
            print(f"Error retrieving triplet data from Elasticsearch: {es_error}")
            return make_response("Error retrieving triplet data", 500)

    def export_triplets_to_sql(self, request=None):
        index_name_triplets = 'triplets'

        try:

            es_data = self.es.search(index=index_name_triplets, size=10000)
            triplets_data = es_data['hits']['hits']

            sql_values = []

            

            for triplet_data in triplets_data:
                triplet_source = triplet_data.get('_source', {})
                article_id = triplet_source.get('article_id', '')
                triplets = triplet_source.get('triplets', [])

                for triplet in triplets:
                    subject_text = triplet.get('subject', {}).get('text', '')
                    relation_text = triplet.get('relation', {}).get('text', '')
                    object_text = triplet.get('object', {}).get('text', '')

                    sql_values.append(f"('{article_id}', '{subject_text}', '{relation_text}', '{object_text}')")

            if sql_values:
                sql_script = 'INSERT INTO triplets_table (article_id, subject_text, relation_text, object_text) VALUES\n'
                sql_script += ',\n'.join(sql_values) + ';'

                response = make_response(sql_script)
                response.headers['Content-Type'] = 'text/sql'
                response.headers['Content-Disposition'] = 'attachment; filename=triplets.sql'

                print("Triplet data exported to SQL script")
            else:
                response = make_response("No triplet data found", 404)

            return response

        except Exception as es_error:
            print(f"Error retrieving triplet data from Elasticsearch: {es_error}")
            return make_response("Error retrieving triplet data", 500)

    def export_my_triplets_to_sql(self, request=None):
        index_name_triplets = 'triplets'
        current_user_id = get_jwt_identity()

        try:
            es_data = self.es.search(index=index_name_triplets, body={
                'query': {
                    'bool': {
                        'must': [
                            {'match': {'path': current_user_id}}
                        ]
                    }
                }
            })

            triplets_data = es_data['hits']['hits']
            sql_values = []



            for triplet_data in triplets_data:
                triplet_source = triplet_data.get('_source', {})
                article_id = triplet_source.get('article_id', '')
                triplets = triplet_source.get('triplets', [])

                for triplet in triplets:
                    subject_text = triplet.get('subject', {}).get('text', '')
                    relation_text = triplet.get('relation', {}).get('text', '')
                    object_text = triplet.get('object', {}).get('text', '')

                    sql_values.append(f"('{article_id}', '{subject_text}', '{relation_text}', '{object_text}')")

            if sql_values:
                sql_script = 'INSERT INTO triplets_table (article_id, subject_text, relation_text, object_text) VALUES\n'
                sql_script += ',\n'.join(sql_values) + ';'

                response = make_response(sql_script)
                response.headers['Content-Type'] = 'text/sql'
                response.headers['Content-Disposition'] = 'attachment; filename=triplets.sql'

                print("Triplet data exported to SQL script")
            else:
                response = make_response("No triplet data found", 404)

            return response

        except Exception as es_error:
            print(f"Error retrieving triplet data from Elasticsearch: {es_error}")
            return make_response("Error retrieving triplet data", 500)
