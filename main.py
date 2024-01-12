from flask import Flask, render_template
from routes.article_routes import articles_routes
from routes.ui_routes import ui_routes
import os
import spacy
from flask_bootstrap import Bootstrap
from dotenv import load_dotenv
from flask_swagger_ui import get_swaggerui_blueprint

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

SWAGGER_URL = '/api/docs'
API_URL = '/static/openapi.json'


swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Test application"
    },
)
app.register_blueprint(swaggerui_blueprint)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
