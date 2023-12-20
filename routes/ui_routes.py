from flask import Blueprint
from flask import  render_template
ui_routes = Blueprint('semantic_ui', __name__)


@ui_routes.route('/semantic_ui/articles_semantic_search')
def semantic_search_articles():
    return render_template('articles_semantic_search.html')
