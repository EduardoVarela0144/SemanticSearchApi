
from flask import jsonify
from elasticsearch import Elasticsearch
from models.article import Article
from werkzeug.utils import secure_filename
import spacy

from elasticsearch.exceptions import NotFoundError
import os

nlp = spacy.load("en_core_web_sm")
es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

class ArticleController:

    def create_article(self, request):
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'})

        folder = request.form.get('folder', 'articles')  
        folder_path = os.path.join('static', folder)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        if file:
            filename = os.path.join(folder_path, secure_filename(file.filename))

            file.save(filename)

            data = request.form.to_dict()
            article = Article(**data, path=folder)
            article.save()

            return jsonify({'message': 'Article created successfully', 'path': f'static/{folder}'})

    
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
    
    def analizar_documento(self, path):
        try:
            index_name = 'articles'  # Nombre del índice de Elasticsearch
            response = es.search(index=index_name, body={
                'query': {
                    'match': {
                        'path': path  # Cambia 'id_article' a 'path'
                    }
                }
            })

            hits = response['hits']['hits']
            if not hits:
                return jsonify({'error': 'Documento no encontrado en Elasticsearch'})

            result = hits[0]['_source']

            doi = result.get('doi', '')
            issn = result.get('issn', '')
            title = result.get('title', '')
            contenido = result.get('results', '')

            doc = nlp(contenido)

            oraciones_y_tripletas = []
            for num, sentence in enumerate(doc.sents):
                triplet_sentence = []

                for token in sentence:
                    if 'VERB' in token.pos_:
                        subject = None
                        verb = token.text
                        objects = []

                        for child in token.children:
                            if 'nsubj' in child.dep_:
                                subject = child.text
                            elif 'obj' in child.dep_:
                                objects.append(child.text)

                        if subject is None:
                            subject = "Not Found"
                        if not objects:
                            objects = ["Not Found"]

                        triplet = {
                            'subject': subject,
                            'relation': verb,
                            'object': ', '.join(objects),
                        }
                        triplet_sentence.append(triplet)

                if triplet_sentence:
                    oraciones_y_tripletas.append({
                        'sentence_number': num,
                        'sentence_text': sentence.text,
                        'triplets': triplet_sentence,
                    })

            respuesta = {
                'doi': doi,
                'issn': issn,
                'title': title,
                'triplets': oraciones_y_tripletas
            }

            index_name_triplets = 'triplets'  # Nombre del índice para almacenar los tripletes
            es.index(index=index_name_triplets, id=path, body={'triplets': oraciones_y_tripletas})

            return jsonify(respuesta)

        except NotFoundError:
            return jsonify({'error': 'Documento no encontrado en Elasticsearch'})

        
        


 