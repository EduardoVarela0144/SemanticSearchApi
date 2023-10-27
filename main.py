import os
from flask import Flask, request, render_template, send_file, jsonify, Blueprint
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import stanza
import spacy

app = Flask(__name__)

stanza.download('en')

nlp = spacy.load("en_core_web_sm")

es = Elasticsearch([{'host': 'localhost', 'port': 9200, 'scheme': 'http'}])

semantic_api = Blueprint('semantic_api', __name__)

app.register_blueprint(semantic_api);


UPLOAD_FOLDER = 'static'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# @app.route('/descargar/<nombre_archivo>', methods=['GET', 'POST'])



# @app.route('/agregar_documento', methods=['POST'])



# @app.route('/analizar_documento/<id_article>', methods=['GET'])



# @app.route('/obtener_tripletas/<id_article>', methods=['GET'])



# @app.route('/analizar_documentos', methods=['POST'])


# @app.route('/semantic_search', methods=['POST'])



if __name__ == '__main__':
    app.run(debug=True)
