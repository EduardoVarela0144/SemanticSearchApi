import os
from flask import Flask, request, render_template, send_file
from elasticsearch import Elasticsearch

import stanza

app = Flask(__name__)

# Descarga e instala los modelos de idioma en inglés
stanza.download('en')

# Inicializa el modelo de idioma en inglés
nlp = stanza.Pipeline('en')

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

            # Realiza el análisis de POS y agrupa las palabras
            doc = nlp(texto)

            palabras_por_etiqueta = {}
            etiquetas_a_excluir = {"AUX", "ADP", "PRON", "NUM", "X", "PART", "SYM", "SCONJ", "CCONJ", "DET", "PUNCT"}

            for sentence in doc.sentences:
                for word in sentence.words:
                    etiqueta_pos = word.pos
                    if etiqueta_pos not in etiquetas_a_excluir:
                        if etiqueta_pos not in palabras_por_etiqueta:
                            palabras_por_etiqueta[etiqueta_pos] = []
                        palabras_por_etiqueta[etiqueta_pos].append(word.text)
                        palabras_por_etiqueta['FILE'] = archivo.filename

            print(palabras_por_etiqueta)


            # Elimina el archivo cargado
            os.remove(filename)

            # Envía los datos a Elasticsearch
            index_name = 'pos_analysis'  
            es.index(index=index_name,  body=palabras_por_etiqueta)


            # Retorna las palabras agrupadas por etiqueta POS
            return render_template('result.html', palabras_por_etiqueta=palabras_por_etiqueta)
        else:
            return "El archivo debe tener la extensión .txt."

    return render_template('index.html')

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
