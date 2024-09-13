from elasticsearch import Elasticsearch, helpers
from collections import defaultdict

es = Elasticsearch("http://localhost:9200")

index_name = "articles"
scroll_size = 1000  
scroll_timeout = "5m" 

scroll_id = None
duplicates = defaultdict(list)

while True:
    query = {
        "_source": ["pmc_id"],  
        "size": scroll_size,
        "sort": [{"_doc": "asc"}]  
    }
    
    if scroll_id:
        response = es.scroll(scroll_id=scroll_id, scroll=scroll_timeout)
    else:
        response = es.search(index=index_name, body=query, scroll=scroll_timeout)
    
    hits = response['hits']['hits']
    if not hits:
        break  
    
    for hit in hits:
        pmc_id = hit['_source']['pmc_id']
        doc_id = hit['_id']
        duplicates[pmc_id].append(doc_id)
    
    scroll_id = response['_scroll_id']

bulk_deletes = []
for pmc_id, doc_ids in duplicates.items():
    if len(doc_ids) > 1:  
        for doc_id in doc_ids[1:]:
            bulk_deletes.append({
                "_op_type": "delete",
                "_index": index_name,
                "_id": doc_id
            })

if bulk_deletes:
    print(f"Preparado para eliminar {len(bulk_deletes)} documentos.")
    success, failed = helpers.bulk(es, bulk_deletes, raise_on_error=True)
    print(f"Eliminados {success} documentos duplicados.")
    if failed:
        print(f"Fallaron {failed} eliminaciones.")
else:
    print("No se encontraron documentos duplicados para eliminar.")

print("Proceso de eliminación de duplicados completado.")


