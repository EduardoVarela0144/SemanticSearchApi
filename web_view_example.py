import streamlit as st
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import os

indexName = "articles"
elasticsearch_password = os.getenv("ELASTICSEARCH_PASSWORD")
elasticsearch_ca_certs = os.getenv("ELASTICSEARCH_CA_CERTS")
elasticsearch_url = os.getenv("ELASTICSEARCH_URL")

try:

    es = Elasticsearch(
        elasticsearch_url,
        basic_auth=("elastic", elasticsearch_password),
        ca_certs=elasticsearch_ca_certs
    )
    
except ConnectionError as e:
    print("Connection Error:", e)

if es.ping():
    print("Succesfully connected to ElasticSearch!!")
else:
    print("Oops!! Can not connect to Elasticsearch!")


def search(input_keyword):
    model = SentenceTransformer('all-mpnet-base-v2')
    vector_of_input_keyword = model.encode(input_keyword)

    query = {
        "field": "vector",
        "query_vector": vector_of_input_keyword,
        "k": 10,
        "num_candidates": 500
    }
    res = es.knn_search(index="articles", knn=query, source=["title", "content"]
                        )
    results = res["hits"]["hits"]

    return results


def main():
    st.title("Razonamiento neuronal de dominio abierto para la reconstrucción e inferencia de conocimiento: una aplicación en enfermedades respiratorias")

    # Input: User enters search query
    search_query = st.text_input("Enter your search query")

    # Button: User triggers the search
    if st.button("Search"):
        if search_query:
            # Perform the search and get results
            results = search(search_query)

            # Display search results
            st.subheader("Search Results")
            for result in results:
                with st.container():
                    if '_source' in result:
                        try:
                            st.header(f"{result['_source']['title']}")
                        except Exception as e:
                            print(e)

                        try:
                            st.write(
                                f"Content: {result['_source']['content']}")
                        except Exception as e:
                            print(e)
                        st.divider()


if __name__ == "__main__":
    main()
