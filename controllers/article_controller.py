import json
import spacy
from flask import jsonify
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

class ArticleController:
    def __init__(self):
        # Configuración de spaCy para inglés
        self.nlp = spacy.load("en_core_web_sm")

        # Configuración de Elasticsearch
        self.es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

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

        for num, sentence in enumerate(sentences):
            triplet_sentence = []

            for token in sentence:
                if 'VERB' in token.pos_:
                    subject = None
                    verb = token.lemma_
                    objects = []

                    # Accessing the head of the token for dependency relation
                    head = token.head
                    if 'nsubj' in token.dep_ and head:
                        subject = head.text
                    elif 'obj' in token.dep_:
                        objects.append(token.text)

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
                sentences_and_triplets.append({
                    'sentence_number': num,
                    'sentence_text': sentence.text if sentence.text else "Not Found",
                    'triplets': triplet_sentence,
                })

        return sentences_and_triplets
