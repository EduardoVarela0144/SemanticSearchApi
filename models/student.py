from elasticsearch import Elasticsearch
import os

elasticsearch_url = os.getenv("ELASTICSEARCH_URL") 

es = Elasticsearch(elasticsearch_url)

class Student:
    def __init__(self, name, age , grade):
        self.name = name
        self.age = age
        self.grade = grade

    def json(self):
        return {
            'name' : self.name,
            'age' : self.age,
            'grade' : self.grade
        }
    
    def save(self):
        if not es.indices.exists(index="students"):
            es.indices.create(index="students")
        es.index(index="students" , body=self.json())

    @classmethod
    def find_by_id(cls, id):
        student = es.get(index="students", id=id)
        if student:
            source = student.get("_source")
            if source:
                return cls(
                        name = source.get("name"),
                        age = source.get("age"),
                        grade = source.get("grade")
                )
        return None
    
    def update(self, data , id):
        es.update(index="students", id=id, body={"doc": data})
    
    def delete(self, id):
        es.delete(index="students", id=id)
    
    @staticmethod
    def search(query):
        body = {
            "query": {
                "match_all": {}
            }
        }
        response = es.search(index="students", body=body)
        return [Student(hit['_source']['name'], hit['_source']['age'], hit['_source']['grade']) for hit in response['hits']['hits']]
