from config.articleMapping import articleMapping
from elasticsearch import Elasticsearch
import spacy
from sentence_transformers import SentenceTransformer
import os

model = SentenceTransformer('all-mpnet-base-v2')

elasticsearch_url = os.getenv("ELASTICSEARCH_URL")


es = Elasticsearch(elasticsearch_url)


nlp = spacy.load("en_core_web_sm")


class Article:
    def __init__(self, title, authors, journal, abstract, doi, issn, year, volume, issue, pages, url, pmc_id, content, path, vector):
        self.title = title
        self.authors = authors
        self.journal = journal
        self.abstract = abstract
        self.doi = doi
        self.issn = issn
        self.year = year
        self.volume = volume
        self.issue = issue
        self.pages = pages
        self.url = url
        self.pmc_id = pmc_id
        self.content = content
        self.path = path
        self.vector = []

    def json(self):
        return {
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'abstract': self.abstract,
            'doi': self.doi,
            'issn': self.issn,
            'year': self.year,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'url': self.url,
            'pmc_id': self.pmc_id,
            'content': self.content,
            'path': self.path,
            'vector': self.vector
        }

    def calculate_and_save_vector(self, text):
        vector = model.encode(text)
        return vector.tolist()

    def save(self):
        self.vector = self.calculate_and_save_vector(self.content)
        if not es.indices.exists(index='articles'):
            es.indices.create(index='articles', mappings=articleMapping)
        es.index(index='articles', body=self.json())

    @classmethod
    def find_by_id(cls, article_id):
        article = es.get(index='articles', id=article_id)
        if article:
            source = article.get('_source')
            if source:
                return cls(
                    title=source.get('title', 'Título no disponible'),
                    authors=source.get('authors', 'Autores no disponibles'),
                    journal=source.get('journal', 'Journal no disponible'),
                    abstract=source.get('abstract', 'Resumen no disponible'),
                    doi=source.get('doi', 'DOI no disponible'),
                    issn=source.get('issn', 'ISSN no disponible'),
                    year=source.get('year', 'Año no disponible'),
                    volume=source.get('volume', 'Volumen no disponible'),
                    issue=source.get('issue', 'Número no disponible'),
                    pages=source.get('pages', 'Páginas no disponibles'),
                    url=source.get('url', 'URL no disponible'),
                    pmc_id=source.get('pmc_id', 'PMC ID no disponible'),
                    content=source.get('content', 'Contenido no disponible'),
                    path=source.get('path', 'Path no disponible'),
                    vector=source.get('vector', 'Vector no disponible')
                )
        return None

    def update(self, data, article_id):
        es.update(index='articles', id=article_id, body={'doc': data})

    def delete(self, article_id):
        es.delete(index='articles', id=article_id)

    @staticmethod
    def search(query):
        body = {
            "query": {
                "match": {
                    "title": query
                }
            }
        }
        result = es.search(index='articles', body=body)
        return [Article(hit['_source']['title']) for hit in result['hits']['hits']]
