import stanza

nlp = stanza.Pipeline(lang='en', processors='tokenize,lemma,pos,ner,depparse')

file_path = 'text_files/PMC1249490.txt'

with open(file_path, 'r', encoding='utf-8') as file:
    text = file.read()

doc = nlp(text)

ner_results = []
dependency_results = []

for sentence in doc.sentences:
    for token in sentence.tokens:
        word = token.text
        ner = token.ner
        dependency_results.append((word))
        ner_results.append((word, ner))

print("Resultados de NER:")
for word, ner in ner_results:
    print(f"Palabra: {word}, NER: {ner}")

print("\nResultados de Análisis de Dependencias:")
for word, head, dependency in dependency_results:
    print(f"Palabra: {word}, Head: {head}, Dependencia: {dependency}")
