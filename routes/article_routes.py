from flask import request, Blueprint
from controllers.article_controller import ArticleController
from flask_jwt_extended import jwt_required

articles_routes = Blueprint('article', __name__)

article_controller = ArticleController()


@articles_routes.route('/article', methods=['POST'])
@jwt_required()
def create_article():
    return article_controller.create_article(request)


@articles_routes.route('/article/<article_id>', methods=['GET'])
@jwt_required()
def get_article(article_id):
    return article_controller.get_article(article_id)


@articles_routes.route('/article/<article_id>', methods=['PUT'])
@jwt_required()
def update_article(article_id):
    return article_controller.update_article(request, article_id)


@articles_routes.route('/article/<article_id>', methods=['DELETE'])
@jwt_required()
def delete_article(article_id):
    return article_controller.delete_article(article_id)


@articles_routes.route('/article', methods=['GET'])
@jwt_required()
def search_articles():
    return article_controller.search_articles(request)


@articles_routes.route('/article/analyze_article', methods=['GET'])
@jwt_required()
def analyze_articles():
    return article_controller.analyze_articles(request)


@articles_routes.route('/article/analyze_all_articles', methods=['GET'])
@jwt_required()
def analyze_all_articles():
    return article_controller.analyze_all_articles(request)


@articles_routes.route('/article/analyze_my_articles', methods=['GET'])
@jwt_required()
def analyze_my_articles():
    return article_controller.analyze_my_articles(request)


@articles_routes.route('/article/get_all_articles', methods=['GET'])
@jwt_required()
def get_all_articles():
    return article_controller.get_all_articles()


@articles_routes.route('/article/get_my_articles', methods=['GET'])
@jwt_required()
def get_my_articles():
    return article_controller.get_my_articles()


@articles_routes.route('/article/articles_semantic_search', methods=['GET'])
@jwt_required()
def search_articles_with_semantic_search():
    query = request.args.get('query')
    top_k = int(request.args.get('top_k'))
    candidates = int(request.args.get('candidates', 500))
    return article_controller.search_articles_with_semantic_search(candidates, top_k, query, request)


@articles_routes.route('/article/post_articles_from_zip', methods=['POST'])
@jwt_required()
def post_articles_in_zip():
    return article_controller.post_articles_in_zip(request)

@articles_routes.route('/article/post_articles_from_folder/<folder>', methods=['POST'])
@jwt_required()
def post_articles_in_folder(folder):
    return article_controller.post_articles_in_folder(folder)
