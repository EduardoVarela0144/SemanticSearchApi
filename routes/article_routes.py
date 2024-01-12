from flask import request, Blueprint
from controllers.article_controller import ArticleController

articles_routes = Blueprint('articles', __name__)

article_controller = ArticleController()

@articles_routes.route('/articles', methods=['POST'])
def create_article():
    return article_controller.create_article(request)

@articles_routes.route('/articles/<article_id>', methods=['GET'])
def get_article(article_id):
    return article_controller.get_article(article_id)

@articles_routes.route('/articles/<article_id>', methods=['PUT'])
def update_article(article_id):
    return article_controller.update_article(request, article_id)

@articles_routes.route('/articles/<article_id>', methods=['DELETE'])
def delete_article(article_id):
    return article_controller.delete_article(article_id)

@articles_routes.route('/articles', methods=['GET'])
def search_articles():
    return article_controller.search_articles(request)

@articles_routes.route('/articles/analyze_articles', methods=['GET'])
def analyze_articles():
    return article_controller.analyze_articles(request)

@articles_routes.route('/articles/analyze_all_articles', methods=['GET'])
def analyze_all_articles():
    return article_controller.analyze_all_articles(request)

@articles_routes.route('/articles/get_all_articles', methods=['GET'])
def get_all_articles():
    return article_controller.get_all_articles()

@articles_routes.route('/articles/articles_semantic_search', methods=['GET'])
def search_articles_with_semantic_search():
    query = request.args.get('query')  
    top_k = int(request.args.get('top_k', 10)) 
    candidates = int(request.args.get('candidates', 500))
    return article_controller.search_articles_with_semantic_search(candidates, top_k, query, request)

@articles_routes.route('/articles/triplets_semantic_search', methods=['GET'])
def search_triplets_with_semantic_search():
    query = request.args.get('query')  
    top_k = int(request.args.get('top_k', 10))
    candidates = int(request.args.get('candidates', 500))
    return article_controller.search_triplets_with_semantic_search(candidates, top_k, query, request)

@articles_routes.route('/articles/download_triplets_csv', methods=['GET'])
def download_triplets_csv():
    return article_controller.export_triplets_to_csv(request)

@articles_routes.route('/articles/download_triplets_sql', methods=['GET'])
def download_triplets_sql():
    return article_controller.export_triplets_to_sql(request)

@articles_routes.route('/articles/post_articles_in_folder/<subfolder_name>', methods=['POST'])
def post_articles_in_folder(subfolder_name):
    return article_controller.post_articles_in_folder(subfolder_name )