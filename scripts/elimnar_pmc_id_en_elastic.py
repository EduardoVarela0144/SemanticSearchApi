from elasticsearch import Elasticsearch

# Conecta a tu instancia de Elasticsearch
es = Elasticsearch("http://localhost:9200")

# Ruta al archivo .txt con los pmc_id duplicados
file_path = "pcm_ids_rep_lote.txt"

# Leer los pmc_id duplicados del archivo .txt
with open(file_path, 'r') as file:
    duplicate_pmc_ids = [line.strip() for line in file.readlines()]

# Iterar sobre cada pmc_id duplicado
for pmc_id in duplicate_pmc_ids:
    try:
        # Buscar documentos con el pmc_id duplicado
        search_results = es.search(index="articles", body={
            "query": {
                "term": {
                    "pmc_id.keyword": pmc_id  # Asegúrate de usar el campo tipo keyword
                }
            },
            "size": 10000  # Ajustar según el tamaño de tus resultados
        })

        # Obtener los IDs de los documentos
        document_ids = [doc['_id'] for doc in search_results['hits']['hits']]

        # Eliminar los documentos duplicados dejando uno
        for doc_id in document_ids[1:]:  # Mantén solo el primer documento
            es.delete(index="articles", id=doc_id)
            print(f"Eliminado documento con ID {doc_id} para pmc_id {pmc_id}")

    except Exception as e:
        print(f"Error al procesar pmc_id {pmc_id}: {str(e)}")

print("Eliminación de duplicados completada.")