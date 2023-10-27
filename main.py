import os
from flask import Flask, request, render_template, send_file, jsonify
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import stanza
import spacy

app = Flask(__name__)

stanza.download('en')

nlp = spacy.load("en_core_web_sm")

es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

UPLOAD_FOLDER = 'static'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/descargar/<nombre_archivo>', methods=['GET', 'POST'])
def descargar_archivo(nombre_archivo):

    try:
        ruta_archivo = f'static/uploads/{nombre_archivo}'
        print(f'Ruta del archivo: {ruta_archivo}')

        return send_file(ruta_archivo, as_attachment=True)

    except FileNotFoundError:
        return "El archivo no se encontró", 404


@app.route('/agregar_documento', methods=['POST'])
def agregar_documento():

    data = request.get_json()

    if data:

        id_article = data.get('id_article', '')
        title = data.get('title', '')
        authors = data.get('authors', '')
        journal = data.get('journal', '')
        issn = data.get('issn', '')
        doi = data.get('doi', '')
        keys = data.get('keys', '')
        abstract = data.get('abstract', '')
        objectives = data.get('objectives', '')
        methods = data.get('methods', '')
        results = data.get('results', '')
        conclusion = data.get('conclusion', '')
        contenido_archivo = data.get('contenido_archivo', '')

        es = Elasticsearch(
            [{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

        documento = {
            'id_article': id_article,
            'title': title,
            'authors': authors,
            'journal': journal,
            'issn': issn,
            'doi': doi,
            'keys': keys,
            'abstract': abstract,
            'objectives': objectives,
            'methods': methods,
            'results': results,
            'conclusion': conclusion,
            'contenido_archivo': contenido_archivo
        }

        index_name = 'articles'
        response = es.index(index=index_name, body=documento)

        if response['result'] == 'created':
            return jsonify({'message': 'Documento agregado con éxito a Elasticsearch'})
        else:
            return jsonify({'message': 'Error al agregar el documento a Elasticsearch'})

    else:
        return jsonify({'message': 'Solicitud no válida. Asegúrate de enviar un formulario JSON válido.'})


@app.route('/analizar_documento/<id_article>', methods=['GET'])
def analizar_documento(id_article):
    try:
        index_name = 'articles'
        response = es.search(index=index_name, body={
            'query': {
                'match': {
                    'id_article': id_article
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
        contenido = result.get('contenido_archivo', '')

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

        index_name_triplets = 'triplets'
        es.index(index=index_name_triplets, id=id_article,
                 body={'triplets': oraciones_y_tripletas})

        return jsonify(respuesta)

    except NotFoundError:
        return jsonify({'error': 'Documento no encontrado en Elasticsearch'})


@app.route('/obtener_tripletas/<id_article>', methods=['GET'])
def obtener_tripletas(id_article):
    try:
        index_name_triplets = 'triplets'
        response = es.get(index=index_name_triplets, id=id_article)

        if response:
            tripletas = response['_source']['triplets']
            return jsonify({'triplets': tripletas})
        else:
            return jsonify({'error': 'Tripletas no encontradas para el ID del artículo'})

    except NotFoundError:
        return jsonify({'error': 'ID del artículo no encontrado en el índice de tripletas'})


@app.route('/analizar_documentos', methods=['POST'])
def analizar_documentos():
    try:

        data = request.get_json()

        if data and 'article_ids' in data:
            article_ids = data['article_ids']

            tripletas_totales = []

            for id_article in article_ids:
                index_name = 'articles'
                response = es.search(index=index_name, body={
                    'query': {
                        'match': {
                            'id_article': id_article
                        }
                    }
                })

                hits = response['hits']['hits']
                if hits:
                    result = hits[0]['_source']

                    doi = result.get('doi', '')
                    issn = result.get('issn', '')
                    title = result.get('title', '')
                    contenido = result.get('contenido_archivo', '')

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

                    tripletas_totales.append(
                        {'id_article': id_article, 'triplets': oraciones_y_tripletas})

            index_name_triplets = 'triplets'
            for tripletas_articulo in tripletas_totales:
                es.index(index=index_name_triplets, id=tripletas_articulo['id_article'], body={
                         'triplets': tripletas_articulo['triplets']})

            return jsonify({'message': 'Tripletas analizadas y guardadas con éxito', 'tripletas': tripletas_totales})

        else:
            return jsonify({'error': 'Solicitud no válida. Asegúrate de enviar un formulario JSON válido con una lista de "article_ids".'})

    except NotFoundError:
        return jsonify({'error': 'Documento no encontrado en Elasticsearch'})


@app.route('/semantic_search', methods=['POST'])
def semantic_search():
    data = request.get_json()
    query = data.get('query', '')
    index_name = data.get('index_name', 'pos_analysis')

    results = es.search(index=index_name, body={
        'query': {
            'match': {
                'contenido_archivo': query
            }
        }
    })

    hits = results['hits']['hits']
    search_results = [hit['_source'] for hit in hits]

    return jsonify(search_results)


if __name__ == '__main__':
    app.run(debug=True)
