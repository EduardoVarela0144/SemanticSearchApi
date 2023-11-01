
from flask import jsonify
from models.article import Article
from werkzeug.utils import secure_filename
import os

class ArticleController:

    def create_article(self, request):
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'})

        if file:
            filename = os.path.join('static/articles', secure_filename(file.filename))

            file.save(filename)

            data = request.form.to_dict()
            article = Article(**data, path=filename)
            article.save()

            return jsonify({'message': 'Article created successfully', 'path': filename})
    
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
        
        


 