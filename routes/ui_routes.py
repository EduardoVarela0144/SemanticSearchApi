from flask import Blueprint, render_template, current_app
ui_routes = Blueprint('semantic_ui', __name__)


@ui_routes.route('/semantic_ui/articles_semantic_search')
def semantic_search_articles():
    return render_template('articles_semantic_search.html')


@ui_routes.route('/semantic_ui/articles')
def show_articles():
    return render_template('articles.html', app=current_app)
