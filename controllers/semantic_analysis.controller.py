# from main import request, es, jsonify

# def semantic_search():
#     data = request.get_json()
#     query = data.get('query', '')
#     index_name = data.get('index_name', 'pos_analysis')

#     results = es.search(index=index_name, body={
#         'query': {
#             'match': {
#                 'contenido_archivo': query
#             }
#         }
#     })

#     hits = results['hits']['hits']
#     search_results = [hit['_source'] for hit in hits]

#     return jsonify(search_results)