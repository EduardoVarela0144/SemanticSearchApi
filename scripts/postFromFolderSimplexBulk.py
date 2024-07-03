import logging
import os
import sys
from elasticsearch import Elasticsearch, helpers
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from tqdm import tqdm
from metapub import PubMedFetcher
import spacy
import gc
import random

model = SentenceTransformer('all-mpnet-base-v2')
nlp = spacy.load("en_core_web_sm")
elasticsearch_url = "http://localhost:9200"
es = Elasticsearch(elasticsearch_url, timeout=60, max_retries=10)

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
    gc.collect()
    return vector.tolist()

def get_article_info(pmc_number):
    fetch = PubMedFetcher()
    try:
        article = fetch.article_by_pmcid(pmc_number)
        if article:
            attributes = ["pmc_id", "title", "authors", "journal", "abstract", "doi", "issn", "year", "volume", "issue", "pages", "url"]
            data = {attr: (getattr(article, attr, '') if getattr(
                article, attr, '') is not None else '') for attr in attributes}
            data["pmc_id"] = pmc_number
            gc.collect()
            return data
    except Exception as e:
        logging.error(f"Error al obtener información del artículo {pmc_number}: {str(e)}")
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

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    articles = []
    actions = []
    all_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    total_files = len(all_files)

    if total_files > 1000000:
        all_files = random.sample(all_files, 1000000)

    for filename in tqdm(all_files, desc="Indexing files"):
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
                        "_index": "articles",
                        "_source": {
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
                    }

                    try:
                        if not es.indices.exists(index='articles'):
                            es.indices.create(index='articles', mappings=articleMapping)

                        if check_unique_pmc_id(pmc_number):
                            actions.append(article_data)
                            if len(actions) >= 500:
                                helpers.bulk(es, actions)
                                actions = []
                            del vector
                            gc.collect()
                        else:
                            logging.info(f"El artículo {pmc_number} ya existe en Elasticsearch.")
                    except Exception as e:
                        logging.error(f"Error al enviar datos a Elasticsearch: {str(e)}")
            except UnicodeDecodeError as e:
                logging.error(f"Error al leer archivo {file_path}: {str(e)}")
            except Exception as e:
                logging.error(f"Error al procesar archivo {file_path}: {str(e)}")
                continue

    if actions:
        helpers.bulk(es, actions)

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
