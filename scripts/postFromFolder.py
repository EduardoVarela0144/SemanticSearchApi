import logging
import os
import sys
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from tqdm import tqdm
from metapub import PubMedFetcher
model = SentenceTransformer('all-mpnet-base-v2')

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

def get_article_info(pmc_number):
    fetch = PubMedFetcher()
    try:
        article = fetch.article_by_pmcid(pmc_number)
        if article:
            return {
                "pmc_id": pmc_number,
                "title": getattr(article, 'title', ''),
                "authors": getattr(article, 'authors', ''),
                "journal": getattr(article, 'journal', ''),
                "abstract": getattr(article, 'abstract', ''),
                "doi": getattr(article, 'doi', ''),
                "issn": getattr(article, 'issn', ''),
                "year": getattr(article, 'year', ''),
                "volume": getattr(article, 'volume', ''),
                "issue": getattr(article, 'issue', ''),
                "pages": getattr(article, 'pages', ''),
                "url": getattr(article, 'url', '')
            }
    except Exception as e:
        print(
            f"Error al obtener información del artículo {pmc_number}: {str(e)}")
    return None


def calculate_and_save_vector(text):
    vector = model.encode(text)
    return vector.tolist()


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


def post_articles_in_folder(folder):
    main_folder = os.environ.get('MAIN_FOLDER')
    folder_path = os.path.join('static', main_folder, folder)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    elasticsearch_url = "http://localhost:9200"
    es = Elasticsearch(elasticsearch_url)

    articles = []

    def check_unique_pmc_id(pmc_id):
        result = es.search(index="articles", q=f"pmc_id:{pmc_id}")
        return result["hits"]["total"]["value"] == 0

    for filename in tqdm(os.listdir(folder_path), desc="Indexando archivos"):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            try:
                content = read_file_with_encodings(file_path)
                pmc_id = os.path.splitext(filename)[0]
                pmc_number = pmc_id.replace("PMC", "")

                article_info = get_article_info(pmc_number)

                if article_info is not None:
                    vector = calculate_and_save_vector(
                        article_info['abstract'])
                    article_data = {
                        "title": article_info['title'],
                        "authors": article_info['authors'],
                        "journal": article_info['journal'],
                        "abstract": article_info['abstract'],
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
                            es.indices.create(
                                index='articles', mappings=articleMapping)
                            
                        if check_unique_pmc_id(pmc_number):
                            es.index(index='articles', document=article_data)
                            articles.append(article_data)
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
