import os
import sys
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from tqdm import tqdm 

model = SentenceTransformer('all-mpnet-base-v2')


def extract_section(content, section_name):
    section_start = content.find(section_name)
    if section_start != -1:
        section_end = content.find('\n', section_start)
        section_block = content[section_end + 1:].strip()
        section_lines = [
            line for line in section_block.splitlines() if line.strip()]
        return ' '.join(map(str, section_lines))
    else:
        return None


def calculate_and_save_vector(text):
    vector = model.encode(text)
    return vector.tolist()


def post_articles_in_folder(folder):
    main_folder = os.environ.get('MAIN_FOLDER')
    folder_path = os.path.join('static', main_folder, folder)

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    elasticsearch_url = os.getenv("ELASTICSEARCH_URL")

    es = Elasticsearch(elasticsearch_url)

    articles = []

    for filename in tqdm(os.listdir(folder_path), desc="Indexando archivos"):
        if filename.endswith('.txt'):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

                title = extract_section(content, "Article")

                methods = extract_section(content, "Methods")
                abstract = extract_section(content, "Introduction")
                results = extract_section(content, "Results")

                pmc_id = os.path.splitext(filename)[0]

                vector = calculate_and_save_vector(content)

                article_data = {
                    "title": title,
                    "authors": None,
                    "journal": None,
                    "issn": None,
                    "doi": None,
                    "pmc_id": pmc_id,
                    "keys": None,
                    "abstract": abstract,
                    "objectives": None,
                    "content": content,
                    "methods": methods,
                    "results": results,
                    "conclusion": None,
                    "path": folder,
                    "vector": vector
                }

                if not es.indices.exists(index='articles'):
                    es.indices.create(index='articles')
                es.index(index='articles', document=article_data)

                articles.append(article_data)

    return articles


if __name__ == "__main__":
    load_dotenv()

    if len(sys.argv) != 2:
        print("Por favor, proporciona el nombre del directorio como argumento.")
        sys.exit(1)

    folder_name = sys.argv[1]
    articles = post_articles_in_folder(folder_name)
    print("Articles extracted and indexed in Elasticsearch.")
