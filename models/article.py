from config.indexMapping import indexMapping
from elasticsearch import Elasticsearch
import spacy
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-mpnet-base-v2')

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elastic", "SZoY=mikTz4MCctIcWhX"),
    ca_certs="/Users/varela/http_ca.crt"
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

    def calculate_and_save_vector(self):
        content = self.content
        self.vector = content.apply(lambda x: model.encode(x))

    def save(self):
        self.calculate_and_save_vector()
        es.indices.create(index='articles', mappings=indexMapping)
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
