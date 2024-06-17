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
            # triplets_count = self.get_triplets_count('triplets')
            articles_count = self.get_index_count('articles')
            
            return jsonify({
                'users': user_count,
                # 'triplets': triplets_count,
                'articles': articles_count,
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
    
    def get_triplets_count(self, index_name):
        try:
            count = 0
            scroll = self.es.search(index=index_name, scroll='1m', size=10000, body={
                "query": {
                    "exists": {"field": "triplets"}
                },
                "_source": ["triplets"]
            })

            while len(scroll['hits']['hits']) > 0:
                for hit in scroll['hits']['hits']:
                    triplets = hit['_source'].get('triplets', [])
                    count += len(triplets)
                
                scroll = self.es.scroll(scroll_id=scroll['_scroll_id'], scroll='1m')
            
            return count

        except NotFoundError:
            return 0