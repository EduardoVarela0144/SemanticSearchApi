from config.articleMapping import articleMapping
from elasticsearch import Elasticsearch
import spacy
from sentence_transformers import SentenceTransformer
import os

model = SentenceTransformer('all-mpnet-base-v2')

elasticsearch_password = os.getenv("ELASTICSEARCH_PASSWORD")
elasticsearch_ca_certs = os.getenv("ELASTICSEARCH_CA_CERTS")

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", elasticsearch_password),
    ca_certs=elasticsearch_ca_certs
)

nlp = spacy.load("en_core_web_sm")


class Article:
    def __init__(self, title, authors, journal, issn, doi, pmc_id, keys, abstract, objectives, content, methods, results, conclusion, path):
        self.title = title
        self.authors = authors
        self.journal = journal
        self.issn = issn
        self.doi = doi
        self.pmc_id = pmc_id
        self.keys = keys
        self.abstract = abstract
        self.objectives = objectives
        self.content = content
        self.methods = methods
        self.results = results
        self.conclusion = conclusion
        self.path = path
        self.vector = []

    def json(self):
        return {
            'title': self.title,
            'authors': self.authors,
            'journal': self.journal,
            'issn': self.issn,
            'doi': self.doi,
            'pmc_id': self.pmc_id,
            'keys': self.keys,
            'abstract': self.abstract,
            'objectives': self.objectives,
            'methods': self.methods,
            'content': self.content,
            'results': self.results,
            'conclusion': self.conclusion,
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
            return cls(source['title'])
        else:
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
