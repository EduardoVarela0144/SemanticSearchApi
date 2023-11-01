from flask import Flask
from routes.article_routes import semantic_api
import os
import stanza
import spacy

app = Flask(__name__)
stanza.download('en')
nlp = spacy.load("en_core_web_sm")

UPLOAD_FOLDER = 'static'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if __name__ == '__main__':
    app.run(debug=True)
    app.register_blueprint(semantic_api)

