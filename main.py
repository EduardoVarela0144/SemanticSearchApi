import os
from flask import Flask, request, render_template

import stanza

app = Flask(__name__)

# Descarga e instala los modelos de idioma en inglés
stanza.download('en')

# Inicializa el modelo de idioma en inglés
nlp = stanza.Pipeline('en')

# Ruta donde se guardarán los archivos subidos
UPLOAD_FOLDER = 'uploaded_files'
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

            # Elimina el archivo cargado
            os.remove(filename)

            # Retorna las palabras agrupadas por etiqueta POS
            return render_template('result.html', palabras_por_etiqueta=palabras_por_etiqueta)
        else:
            return "El archivo debe tener la extensión .txt."

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
