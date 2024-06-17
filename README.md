# Comandos para levantar contenedores

### Instalar dependencias del backend
pip install -r requirements.txt

### Flask
- docker-compose -f docker-compose.semantic-api.yml build
- docker-compose -f docker-compose.semantic-api.yml up

### ElasticSearch
- docker-compose -f docker-compose.elasticsearch.yml up

### Correr en local
- export FLASK_APP=main.py Mac
- set FLASK_APP=main.py  Windows
- flask run --debug --host=0.0.0.0

# Env
ELASTICSEARCH_URL=http://localhost:9200

BASE_URL=http://127.0.0.1:5000

MAIN_FOLDER=/ruta_donde_se_guardaran_txt

SECRET=servicio

THREADS=2

MEMORY=4G

ES_JAVA_OPTS=-Xms4g -Xmx4g
