
from flask import request, Blueprint
from controllers.triplets_controller import TripletsController

triplets_routes = Blueprint('triplet', __name__)

triplets_controller = TripletsController()

@triplets_routes.route('/triplet/get_all_triplets', methods=['GET'])
def get_all_triplets():
    return triplets_controller.get_all_triplets()

@triplets_routes.route('/triplet/triplets_semantic_search', methods=['GET'])
def search_triplets_with_semantic_search():
    query = request.args.get('query')  
    top_k = int(request.args.get('top_k', 10))
    candidates = int(request.args.get('candidates', 500))
    return triplets_controller.search_triplets_with_semantic_search(candidates, top_k, query, request)

@triplets_routes.route('/triplet/download_triplets_csv', methods=['GET'])
def download_triplets_csv():
    return triplets_controller.export_triplets_to_csv(request)

@triplets_routes.route('/triplet/download_triplets_sql', methods=['GET'])
def download_triplets_sql():
    return triplets_controller.export_triplets_to_sql(request)