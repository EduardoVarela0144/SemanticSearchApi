from elasticsearch import Elasticsearch

es = Elasticsearch("http://192.100.170.206:9200")

index_name = "articles"

query = {
    "query": {
        "match": {
            "path": "T1"
        }
    }
}

response = es.search(index=index_name, body=query)

total_results = response['hits']['total']['value']

print(f"Total de resultados encontrados: {total_results}")
