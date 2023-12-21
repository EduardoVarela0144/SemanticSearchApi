FROM python:3.11

COPY --from=openjdk:8-jre-slim /usr/local/openjdk-8 /usr/local/openjdk-8

ENV JAVA_HOME /usr/local/openjdk-8

RUN update-alternatives --install /usr/bin/java java /usr/local/openjdk-8/bin/java 1

ENV OPENBLAS_NUM_THREADS=1

ADD . /app
WORKDIR /app
RUN pip install --progress-bar off -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -c 'import stanza; stanza.install_corenlp(); stanza.download("en");'

EXPOSE 5000

CMD ["python", "main.py"]