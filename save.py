import stanza
import os

# Descarga e instala los modelos de idioma en inglés
stanza.download('en')

# Inicializa el modelo de idioma en inglés
nlp = stanza.Pipeline('en')

# Ruta al archivo .txt que deseas procesar
ruta_archivo = "text_files/PMC1249490.txt"

# Etiquetas POS a excluir
etiquetas_a_excluir = {"AUX", "ADP", "PRON", "NUM", "X", "PART", "SYM", "SCONJ", "CCONJ", "DET", "PUNCT"}

# Verifica si el archivo existe en la ruta especificada
if os.path.exists(ruta_archivo):
    # Lee el contenido del archivo .txt
    with open(ruta_archivo, "r", encoding="utf-8") as archivo:
        texto = archivo.read()

    # Procesa el texto
    doc = nlp(texto)

    # Crear diccionarios para agrupar palabras por etiqueta POS
    palabras_por_etiqueta = {}

    # Análisis de dependencias y entidades nombradas
    for sentence in doc.sentences:
        for word in sentence.words:
            etiqueta_pos = word.pos

            # Excluye las etiquetas especificadas
            if etiqueta_pos not in etiquetas_a_excluir:
                # Agrega la palabra al diccionario correspondiente
                if etiqueta_pos not in palabras_por_etiqueta:
                    palabras_por_etiqueta[etiqueta_pos] = []
                palabras_por_etiqueta[etiqueta_pos].append(word.text)

    # Imprimir palabras agrupadas por etiqueta POS
    for etiqueta, palabras in palabras_por_etiqueta.items():
        palabras_coma = ', '.join(palabras)
        print(f"Etiqueta POS: {etiqueta}\nPalabras: {palabras_coma}\n")
else:
    print(f"El archivo {ruta_archivo} no existe.")
