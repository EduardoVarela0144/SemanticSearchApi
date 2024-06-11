import logging
import os
import sys
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from tqdm import tqdm
from metapub import PubMedFetcher
from elasticsearch.helpers import scan
from stanza.server import CoreNLPClient
from elasticsearch.exceptions import NotFoundError
import spacy
import time

model = SentenceTransformer('all-mpnet-base-v2')
nlp = spacy.load("en_core_web_sm")
elasticsearch_url = "http://localhost:9200"
es = Elasticsearch(elasticsearch_url)

articleMapping = {
    "properties": {
        "title": {
            "type": "text"
        },
        "authors": {
            "type": "keyword",
            "ignore_above": 256
        },
        "journal": {
            "type": "text"
        },
        "abstract": {
            "type": "text"
        },
        "doi": {
            "type": "text"
        },
        "issn": {
            "type": "text"
        },
        "year": {
            "type": "text"
        },
        "volume": {
            "type": "text"
        },
        "issue": {
            "type": "text"
        },
        "pages": {
            "type": "text"
        },
        "url": {
            "type": "text"
        },
        "pmc_id": {
            "type": "text",
            "fields": {
                    "keyword": {
                        "type": "keyword"
                    }
            }, },
        "content": {
            "type": "text"
        },
        "path": {
            "type": "text"
        },
        "vector": {
            "type": "dense_vector",
            "dims": 768,
            "index": True,
            "similarity": "l2_norm"
        }

    }
}

def calculate_and_save_vector(text):
    vector = model.encode(text)
    return vector.tolist()


def extract_triplets(sentences, memory, threads):
    sentences_and_triplets = []


    with CoreNLPClient(annotators=["openie", "coref"], be_quiet=True, memory=memory, threads=threads) as client:
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


def post_triplets_with_vectors(result):
    index_name_triplets_vector = 'triplets'

    if not es.indices.exists(index=index_name_triplets_vector):
        es.indices.create(index=index_name_triplets_vector)

    article_id = result.get('article_id')
    data_analysis_list = result.get('data_analysis', [])

    for data_analysis in data_analysis_list:
        sentence_text_vector = data_analysis.get('sentence_text_vector')
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
                es.index(index=index_name_triplets_vector, document=triplet_vector_data)
            except Exception as es_error:
                print(f"Error indexing triplet vector data into Elasticsearch: {es_error}")

def get_article_info(pmc_number):
    fetch = PubMedFetcher()
    try:
        article = fetch.article_by_pmcid(pmc_number)
        if article:
            attributes = ["pmc_id", "title", "authors", "journal", "abstract", "doi", "issn", "year", "volume", "issue", "pages", "url"]
            data = {attr: (getattr(article, attr, '') if getattr(article, attr, '') is not None else '') for attr in attributes}
            data["pmc_id"] = pmc_number 
            return data
    except Exception as e:
        print(f"Error al obtener información del artículo {pmc_number}: {str(e)}")
    return None

def read_file_with_encodings(file_path):
    encodings = ['utf-8', 'latin-1']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(
        f"Cannot decode file {file_path} with available encodings.")

def check_unique_pmc_id(pmc_id):
    result = es.search(index="articles", q=f"pmc_id:{pmc_id}")
    return result["hits"]["total"]["value"] == 0

def post_articles_in_folder(folder):
    main_folder = os.environ.get('MAIN_FOLDER')
    folder_path = os.path.join('static', main_folder, folder)
    threads = os.environ.get('THREADS')
    memory = os.environ.get('MEMORY')

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


    articles = []

    

    for filename in tqdm(os.listdir(folder_path), desc="Indexando archivos"):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            try:
                content = read_file_with_encodings(file_path)

                pmc_id = os.path.splitext(filename)[0]
                pmc_number = pmc_id.replace("PMC", "")



                article_info = get_article_info(pmc_number)



                if article_info is not None:
                    abstract_or_content = article_info['abstract'] if article_info['abstract'] != '' else content
                    vector = calculate_and_save_vector(abstract_or_content)
                    article_data = {
                        "title": article_info['title'],
                        "authors": article_info['authors'],
                        "journal": article_info['journal'],
                        "abstract": abstract_or_content,
                        "doi": article_info['doi'],
                        "issn": article_info['issn'],
                        "year": article_info['year'],
                        "volume": article_info['volume'],
                        "issue": article_info['issue'],
                        "pages": article_info['pages'],
                        "url": article_info['url'],
                        "pmc_id": article_info['pmc_id'],
                        "content": content,
                        "path": folder,
                        "vector": vector
                    }


                    try:
                        if not es.indices.exists(index='articles'):
                            es.indices.create(index='articles', mappings=articleMapping)
                            
                        if check_unique_pmc_id(pmc_number):

                            es.index(index='articles', document=article_data)

                            articles.append(article_data)

                            doc = nlp(content)

                            sentences_and_triplets = extract_triplets(doc.sents, memory, threads)

                            result = es.search(index='articles', body={"query": {"match": {"pmc_id": pmc_number}}})
                            article_id = result['hits']['hits'][0]['_id']
                            print(f"Article ID: {article_id}")

                            response = {
                                    'article_id': article_id,
                                    'article_title': article_info['title'],
                                    'data_analysis': sentences_and_triplets,
                                    'pmc_id': pmc_number,
                            }

                            post_triplets_with_vectors(response)


                        else:
                            print(f"El artículo {pmc_number} ya existe en Elasticsearch.")
                    except Exception as e:
                        print(
                            f"Error al enviar datos a Elasticsearch: {str(e)}")
            except UnicodeDecodeError as e:
                print(f"Error al leer archivo {file_path}: {str(e)}")
            except Exception as e:
                print(f"Error al procesar archivo {file_path}: {str(e)}")
                continue

    return articles


if __name__ == "__main__":
    load_dotenv()

    logger = logging.getLogger()
    logger.setLevel(logging.CRITICAL)

    if len(sys.argv) != 2:
        print("Por favor, proporciona el nombre del directorio como argumento.")
        sys.exit(1)

    folder_name = sys.argv[1]
    articles = post_articles_in_folder(folder_name)
    print("Articles extracted and indexed in Elasticsearch.")
