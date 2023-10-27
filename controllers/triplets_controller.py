# from main import es, jsonify, NotFoundError

# def obtener_tripletas(id_article):
#     try:
#         index_name_triplets = 'triplets'
#         response = es.get(index=index_name_triplets, id=id_article)

#         if response:
#             tripletas = response['_source']['triplets']
#             return jsonify({'triplets': tripletas})
#         else:
#             return jsonify({'error': 'Tripletas no encontradas para el ID del artículo'})

#     except NotFoundError:
#         return jsonify({'error': 'ID del artículo no encontrado en el índice de tripletas'})