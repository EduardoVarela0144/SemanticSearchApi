from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from stanza.server import CoreNLPClient
from elasticsearch.exceptions import NotFoundError
import sys
import spacy
from tqdm import tqdm
import logging

elasticsearch_url = "http://localhost:9200"
es = Elasticsearch(elasticsearch_url)
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-mpnet-base-v2')

def calculate_and_save_vector(text):
    vector = model.encode(text)
    return vector.tolist()


def extract_triplets(sentences, memory, threads):
    sentences_and_triplets = []

    with CoreNLPClient(annotators=["openie"], be_quiet=False, max_mem=memory, threads=threads) as client:
        for span in sentences:
            if span.text:
                text = span.text
                ann = client.annotate(text)
                triplet_sentence = []

                for sentence in ann.sentence:
                    for triple in sentence.openieTriple:

                        triplet = {
                            'subject': {'text': triple.subject},
                            'relation': {'text': triple.relation},
                            'object': {'text': triple.object},
                        }

                        triplet_sentence.append(triplet)

                if triplet_sentence:
                    sentences_and_triplets.append({
                        'sentence_text': text,
                        'sentence_text_vector': calculate_and_save_vector(text),
                        'triplets': triplet_sentence,
                    })

    return sentences_and_triplets



def post_triplets_with_vectors(result_collection):
    index_name_triplets_vector = 'triplets_vector'

    if not es.indices.exists(index=index_name_triplets_vector):
        es.indices.create(
            index=index_name_triplets_vector)

    for result in result_collection:
        article_id = result.get('article_id')
        data_analysis_list = result.get('data_analysis', [])

        try:
            for data_analysis in data_analysis_list:
                sentence_text_vector = data_analysis.get(
                    'sentence_text_vector')
                sentence_text = data_analysis.get('sentence_text')
                triplets = data_analysis.get('triplets')

                if all([article_id, sentence_text_vector, sentence_text]):
                    triplet_vector_data = {
                        'article_id': article_id,
                        'sentence_text_vector': sentence_text_vector,
                        'sentence_text': sentence_text,
                        'triplets': triplets
                    }

                    try:
                        es.index(
                            index=index_name_triplets_vector, body=triplet_vector_data)
                        # print("Indexed successfully.")
                    except Exception as es_error:
                        print(
                            f"Error indexing triplet vector data into Elasticsearch: {es_error}")
                else:
                    print(
                        "Skipping data analysis due to missing values:", data_analysis)
        except Exception as result_error:
            print(f"Error processing result: {result_error}")


def analyze_articles(folder):
    try:
        result_collection = []

        index_name = 'articles'
        index_name_triplets = 'triplets'

        threads = 2
        memory = 4


        if not es.indices.exists(index=index_name_triplets):
            es.indices.create(
                index=index_name_triplets)

        current_user_id = folder

        response = es.search(index=index_name, q=f"path:{current_user_id}")



        hits = response.get('hits', {}).get('hits', [])
        if not hits:
            print('Document not found in Elasticsearch')

        for hit in tqdm(hits, desc="Processing articles"):
            result = hit.get('_source', {})
            article_id = hit.get('_id', '')
            title = result.get('title', '')
            content = result.get('content', '')
            folder = result.get('path', '')

            doc = nlp(content)
            

            sentences_and_triplets = extract_triplets(doc.sents, memory, threads)

            response = {
                'article_id': article_id,
                'article_title': title,
                'path': folder,
                'data_analysis': sentences_and_triplets
            }

            try:
                es.index(index=index_name_triplets, body=response)
            except Exception as es_error:
                print(
                    f"Error indexing data into Elasticsearch: {es_error}")

            result_collection.append(response)

        post_triplets_with_vectors(result_collection)

        for item in result_collection:
            for analysis_item in item['data_analysis']:
                analysis_item.pop('sentence_text_vector', None)

        return result_collection

    except NotFoundError:
        return {'error': f'Document not found in Elasticsearch'}

    except Exception as e:
        return {'error': f'Error during analysis: {str(e)}'}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Por favor, proporciona el nombre del directorio como argumento.")
        sys.exit(1)

    folder_name = sys.argv[1]
    analysis_result = analyze_articles(folder_name)
    if 'error' in analysis_result:
        print("Error:", analysis_result['error'])
    else:
        print("Articles analyzed and indexed in Elasticsearch.")
