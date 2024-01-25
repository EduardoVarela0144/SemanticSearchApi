from flask import jsonify
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import os

class StatisticsController:
    def __init__(self):

        elasticsearch_url = os.getenv("ELASTICSEARCH_URL")
        self.es = Elasticsearch(elasticsearch_url)

    def get_index_counts(self):
        try:
            user_count = self.get_index_count('users')
            triplets_count = self.get_index_count('triplets')
            articles_count = self.get_index_count('articles')
            triplets_vector_count = self.get_index_count('triplets_vector')

            return jsonify({
                'users': user_count,
                'triplets': triplets_count,
                'articles': articles_count,
                'triplets_vector': triplets_vector_count
            })

        except Exception as e:
            return jsonify({'error': f'Error retrieving index counts: {str(e)}'})

    def get_index_count(self, index_name):
        try:
            response = self.es.count(index=index_name, body={
                'query': {
                    'match_all': {}
                }
            })
            return response.get('count', 0)

        except NotFoundError:
            return 0
