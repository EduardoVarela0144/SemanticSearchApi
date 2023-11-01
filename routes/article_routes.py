from flask import request, Blueprint
from controllers.article_controller import ArticleController

semantic_api = Blueprint('articles', __name__)

article_controller = ArticleController()

@semantic_api.route('/articles', methods=['POST'])
def create_article():
    return article_controller.create_article(request)

@semantic_api.route('/articles/<article_id>', methods=['GET'])
def get_article(article_id):
    return article_controller.get_article(article_id)

@semantic_api.route('/articles/<article_id>', methods=['PUT'])
def update_article(article_id):
    return article_controller.update_article(request, article_id)

@semantic_api.route('/articles/<article_id>', methods=['DELETE'])
def delete_article(article_id):
    return article_controller.delete_article(article_id)

@semantic_api.route('/articles', methods=['GET'])
def search_articles():
    return article_controller.search_articles(request)
