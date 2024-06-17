# Comandos para levantar contenedores

### Flask
- docker-compose -f docker-compose.semantic-api.yml build
- docker-compose -f docker-compose.semantic-api.yml up

### ElasticSearch
- docker-compose -f docker-compose.elasticsearch.yml up

# Env
ELASTICSEARCH_URL=http://localhost:9200

BASE_URL=http://127.0.0.1:5000

MAIN_FOLDER=/ruta_donde_se_guardaran_txt

SECRET=servicio

THREADS=2

MEMORY=4G

ES_JAVA_OPTS=-Xms4g -Xmx4g
