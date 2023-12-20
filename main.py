from flask import Flask, render_template
from routes.article_routes import articles_routes
from routes.ui_routes import ui_routes
import os
import spacy
from flask_bootstrap import Bootstrap
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.register_blueprint(articles_routes)
app.register_blueprint(ui_routes)
bootstap = Bootstrap(app)

nlp = spacy.load("en_core_web_sm")

UPLOAD_FOLDER = 'static'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['BASE_URL'] = os.getenv('BASE_URL')

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

