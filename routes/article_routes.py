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

@articles_routes.route('/articles/analizar_documento/<id_article>', methods=['GET'])
def analizar(id_article):
    return article_controller.analizar_documento(id_article)