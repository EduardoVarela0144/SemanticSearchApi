import json
import spacy
from flask import jsonify
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
from stanza.server import CoreNLPClient

import os
from models.article import Article
from werkzeug.utils import secure_filename

class ArticleController:
    def __init__(self):
        # Configuración de spaCy para inglés
        self.nlp = spacy.load("en_core_web_sm")

        # Configuración de Elasticsearch
        self.es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

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
    
    def analyze_documents(self, path):
        try:
            result_collection = []

            index_name = 'articles'
            response = self.es.search(index=index_name, body={
                'query': {
                    'match': {
                        'path': path
                    }
                }
            })

            hits = response.get('hits', {}).get('hits', [])
            if not hits:
                return jsonify({'error': f'Document not found in Elasticsearch for path: {path}'})

            for hit in hits:
                result = hit.get('_source', {})
                doi = result.get('doi', '')
                issn = result.get('issn', '')
                title = result.get('title', '')
                content = result.get('results', '')
                folder = result.get('path', '')

                # Analizar el contenido con spaCy
                doc = self.nlp(content)
                sentences_and_triplets = self.extract_triplets(doc.sents)

                response = {
                    'doi': doi,
                    'path': folder,
                    'issn': issn,
                    'title': title,
                    'triplets': sentences_and_triplets
                }

                index_name_triplets = 'triplets'
                self.es.index(index=index_name_triplets, id=hit.get('_id'), body={'triplets': sentences_and_triplets})

                result_collection.append(response)

            return jsonify(result_collection)

        except NotFoundError:
            return jsonify({'error': f'Document not found in Elasticsearch for path: {path}'})

        except Exception as e:
            return jsonify({'error': f'Error during analysis: {str(e)}'})

    def extract_triplets(self, sentences):
        sentences_and_triplets = []

        with CoreNLPClient(annotators=["openie"], be_quiet=False, ) as client:
            for text in sentences:
                ann = client.annotate(text)
                for sentence in ann.sentence:
                    triplet_sentence = []
                    for triple in sentence.openieTriple:

                        triplet = {
                        'subject': triple.subject,
                        'relation': triple.relation,
                        'object': triple.object,
                        }
                        triplet_sentence.append(triplet)

                    if triplet_sentence:
                        sentences_and_triplets.append({
                            #'sentence_number': num,
                            'sentence_text': sentence.text if sentence.text else "Not Found",
                            'triplets': triplet_sentence,
                        })

        return sentences_and_triplets
