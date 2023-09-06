from pathlib import Path
from flask import Flask, request, jsonify
from stanza.server import CoreNLPClient
from elasticsearch import Elasticsearch

app = Flask(__name__)

# Configure Elasticsearch
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

# Configure Stanford CoreNLP client
stanford_corenlp_path = 'path/to/stanford-corenlp'
with CoreNLPClient(annotators=['openie'], timeout=30000, endpoint='http://localhost:9000') as client:
    pass  # Warm-up the client

@app.route('/')
def hello():
    return "Semantic Api"

@app.route('/extract', methods=['POST'])
def extract_information():
    if 'directory_path' not in request.form:
        return jsonify({"error": "Directory path not provided"}), 400

    directory_path = request.form['directory_path']
    document_files = list(Path(directory_path).glob("*.txt"))

    for file_path in document_files:
        with open(file_path, 'r') as file:
            document_text = file.read()

        # Extract information using Stanford CoreNLP's OpenIE
        with CoreNLPClient(annotators=['openie'], timeout=30000, endpoint='http://localhost:9000') as client:
            ann = client.annotate(document_text)
            for sentence in ann.sentence:
                for triple in sentence.openieTriple:
                    extraction = {
                        'subject': triple.subject,
                        'relation': triple.relation,
                        'object': triple.object,
                        'document': str(file_path)
                    }
                    # Store the extraction in Elasticsearch
                    es.index(index='extractions', body=extraction)

    return jsonify({"message": "Extractions stored successfully"})

if __name__ == '__main__':
    app.run(debug=True)
