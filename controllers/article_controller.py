
from flask import jsonify
from models.article import Article
import os

class ArticleController:

    def create_article(self, request):
        data = request.get_json()
        article = Article(data['title'], data['authors'], data['journal'], data['issn'], data['doi'], data['pmc_id'], data['keys'], data['abstract'], data['objectives'], data['methods'], data['results'], data['conclusion'], data['path'])
        article.save()
        filename = os.path.join('static/articles', 'article.txt')
        with open(filename, 'w') as file:
            file.write(article.serialize())  


        return jsonify({'message': 'Article created successfully'})
    
    def get_article(self, article_id):
        article = Article.find_by_id(article_id)
        return jsonify(article.json())

    def update_article(self, request, article_id):
        data = request.get_json()
        article = Article.find_by_id(article_id)
        if article:
            article.update(data)
            return jsonify({'message': 'Updated article'})
        else:
            return jsonify({'message': 'Article not found'}, 404)

    def delete_article(self, article_id):
        article = Article.find_by_id(article_id)
        if article:
            article.delete()
            return jsonify({'message': 'Article removed'})
        else:
            return jsonify({'message': 'Article not found'}, 404)

    def search_articles(self, request):
        query = request.args.get('query')
        articles = Article.search(query)
        return jsonify([article.json() for article in articles])
        
        


 