import spacy
from flask import jsonify, make_response
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from stanza.server import CoreNLPClient
import os
from sentence_transformers import SentenceTransformer
from config.tripletsVectorMapping import tripletsVectorMapping
import threading
import pandas as pd
from io import StringIO

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
            index="triplets_vector",
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
        index_name_triplets_vector = 'triplets_vector'

        if not self.es.indices.exists(index=index_name_triplets_vector):
            self.es.indices.create(
                index=index_name_triplets_vector, mappings=tripletsVectorMapping)

        for result in result_collection:
            article_id = result.get('article_id')
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
                            'triplets': triplets
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
                article_title = result.get('article_title', '')
                path = result.get('path', '')
                sentences_and_triplets = result.get('data_analysis', [])

                result_collection.append({
                    'id': triplet_id,
                    'article_id': article_id,
                    'article_title': article_title,
                    'path': path,
                    'data_analysis': [
                        {
                            'sentence_text': item['sentence_text'],
                            'triplets': item['triplets']
                        } for item in sentences_and_triplets
                    ]
                })

            return jsonify(result_collection)

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

                data_analysis_list = triplet_source.get('data_analysis', [])

                for data_analysis in data_analysis_list:
                    sentence_text = data_analysis.get('sentence_text', '')

                    triplets = data_analysis.get('triplets', [])

                    for triplet in triplets:
                        subject_text = triplet.get(
                            'subject', {}).get('text', '')
                        relation_text = triplet.get(
                            'relation', {}).get('text', '')
                        object_text = triplet.get('object', {}).get('text', '')

                        flattened_triplet = {
                            'article_id': article_id,
                            'sentence_text': sentence_text,
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
            print(
                f"Error retrieving triplet data from Elasticsearch: {es_error}")
            return make_response("Error retrieving triplet data", 500)

    def export_triplets_to_sql(self, request=None):
        index_name_triplets = 'triplets'

        try:
            es_data = self.es.search(index=index_name_triplets, size=10000)
            triplets_data = es_data['hits']['hits']

            sql_content = "-- Triplet data\n\n"

            for triplet_data in triplets_data:
                triplet_source = triplet_data.get('_source', {})

                article_id = triplet_source.get('article_id', '')
                article_title = triplet_source.get('article_title', '')

                data_analysis_list = triplet_source.get('data_analysis', [])

                for data_analysis in data_analysis_list:
                    sentence_text = data_analysis.get('sentence_text', '')

                    triplets = data_analysis.get('triplets', [])

                    for triplet in triplets:
                        subject_text = triplet.get(
                            'subject', {}).get('text', '')
                        relation_text = triplet.get(
                            'relation', {}).get('text', '')
                        object_text = triplet.get('object', {}).get('text', '')

                        sql_content += (
                            f"INSERT INTO triplets_table (article_id, article_title, sentence_text, "
                            f"subject_text, relation_text, object_text) "
                            f"VALUES ('{article_id}', '{article_title}', '{sentence_text}', "
                            f"'{subject_text}', '{relation_text}', '{object_text}');\n"
                        )

            response = make_response(sql_content)
            response.headers['Content-Type'] = 'application/sql'
            response.headers['Content-Disposition'] = 'attachment; filename=triplets.sql'

            print("Triplet data exported to SQL")

            return response

        except Exception as es_error:
            print(
                f"Error retrieving triplet data from Elasticsearch: {es_error}")
            return make_response("Error retrieving triplet data", 500)
