FROM python:3.11
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm
EXPOSE 8087  
CMD ["python", "main.py"]