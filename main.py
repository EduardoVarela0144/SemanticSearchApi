from flask import Flask
from routes.article_routes import articles_routes
import os
import stanza
import spacy

app = Flask(__name__)
app.register_blueprint(articles_routes)

stanza.download('en')
nlp = spacy.load("en_core_web_sm")

UPLOAD_FOLDER = 'static'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


if __name__ == '__main__':
    app.run(debug=True)

