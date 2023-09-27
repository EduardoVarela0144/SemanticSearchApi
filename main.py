import os
from flask import Flask, request, render_template, send_file
from elasticsearch import Elasticsearch
import stanza
import spacy

app = Flask(__name__)

# Descarga e instala los modelos de idioma en inglés
stanza.download('en')

# Inicializa el modelo de idioma en inglés
#nlp = stanza.Pipeline('en')
nlp = spacy.load("en_core_web_sm")

# Inicializa la conexión a Elasticsearch
es = Elasticsearch([{'host': 'localhost', 'port': 9200,'scheme':'http' }])  # Reemplaza con la dirección de tu servidor Elasticsearch


# Ruta donde se guardarán los archivos subidos
UPLOAD_FOLDER = 'static'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        archivo = request.files['file']
        if not archivo:
            return "Por favor, seleccione un archivo para subir."

        # Verifica la extensión del archivo
        if archivo.filename.endswith('.txt'):
            # Guarda el archivo en el directorio de carga
            filename = os.path.join(UPLOAD_FOLDER, archivo.filename)
            archivo.save(filename)

            # Procesa el texto del archivo
            with open(filename, "r", encoding="utf-8") as file:
                texto = file.read()

            # Split text into sentences using spaCy
            doc_spacy = list(nlp(texto).sents)

            oraciones_y_tripletas = []

            for sentence in doc_spacy:
                triplet_sentence = []

                for token in sentence:
                    if 'VERB' in token.pos_:
                        subject = None
                        verb = token.text
                        objects = []

                        # Iterate over the token's children to find subjects and objects
                        for child in token.children:
                            if 'nsubj' in child.dep_:
                                subject = child.text
                            elif 'obj' in child.dep_:
                                objects.append(child.text)

                        # Create triplet with "Not Found" if subject or object is missing
                        if subject is None:
                            subject = "Not Found"
                        if not objects:
                            objects = ["Not Found"]

                        # Create a triplet even if only one object is found
                        triplet = {
                            'subject': subject,
                            'relation': verb,
                            'object': ', '.join(objects),
                        }
                        triplet_sentence.append(triplet)

                # Append the sentence and its triplets to the result list
                if triplet_sentence:
                    oraciones_y_tripletas.append({
                        'sentence': sentence.text,
                        'triplets': triplet_sentence,
                    })

            # Elimina el archivo cargado
            os.remove(filename)

            if not oraciones_y_tripletas:
                return "No se encontraron oraciones y triplets."

            # Envía los datos a Elasticsearch
            index_name = 'pos_analysis'
            es.index(index=index_name, body={'data': oraciones_y_tripletas})

            # Retorna las oraciones y tripletas
            return render_template('result.html', oraciones_y_tripletas=oraciones_y_tripletas)
        else:
            return "El archivo debe tener la extensión .txt."

    return render_template('index.html')

# ... (other imports and app setup)



@app.route('/descargar/<nombre_archivo>',methods=['GET', 'POST'])
def descargar_archivo(nombre_archivo):

    try:
        # Especifica la ruta completa del archivo dentro de la carpeta 'static'
        ruta_archivo = f'static/uploads/{nombre_archivo}'
        print(f'Ruta del archivo: {ruta_archivo}')

        # Usa la función send_file para enviar el archivo al cliente
        return send_file(ruta_archivo, as_attachment=True)

    except FileNotFoundError:
        # Manejo de errores si el archivo no se encuentra
        return "El archivo no se encontró", 404

@app.route('/semantic_search', methods=['GET'])
def index():
    return render_template('search.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form['query']

    # Realiza la búsqueda en Elasticsearch
    index_name = 'pos_analysis'  # Nombre del índice en Elasticsearch
    results = es.search(index=index_name, body={
        'query': {
            #'match': {
               # 'words': query
            #}
             'simple_query_string' : {"query": query}
        }
    })

    # Procesa los resultados de la búsqueda
    hits = results['hits']['hits']
    search_results = []
    for hit in hits:
        hit_source = hit['_source']
        search_results.append(hit_source)
    
        # Diccionario para almacenar el contenido de los archivos
    file_contents = {}

    # Leer el contenido de los archivos y almacenarlo en el diccionario
    for result in search_results:
        if 'FILE' in result:
            filename = result['FILE']
            file_path = os.path.join("static/uploads/", filename)
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_contents[filename] = file.read()

    return render_template('search_results.html', query=query, results=search_results, file_contents=file_contents)

if __name__ == '__main__':
    app.run(debug=True)
