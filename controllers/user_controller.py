from flask import jsonify, make_response
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError
import os
from passlib.hash import bcrypt
from flask_jwt_extended import create_access_token
from elasticsearch.helpers import scan


class UserController:
    def __init__(self):

        elasticsearch_url = os.getenv("ELASTICSEARCH_URL")
        self.es = Elasticsearch(elasticsearch_url)

    def register_user(self, request):
        user_data = request.get_json()
        if not all(key in user_data for key in ['name', 'lastname', 'email', 'password']):
            return jsonify({'error': 'Incomplete user data'}), 400

        try:
            email_exists = self.check_email_exists(user_data['email'])
            if email_exists:
                return jsonify({'error': 'Email already registered'}), 400
        except NotFoundError:
            hashed_password = bcrypt.hash(user_data['password'])
            user_data['password'] = hashed_password

            self.es.index(index='users', body=user_data)
            return jsonify({'message': 'User registered successfully'}), 201

    def login_user(self, request):
        login_data = request.get_json()

        if not all(key in login_data for key in ['email', 'password']):
            return jsonify({'error': 'Incomplete login data'}), 400

        user_data = self.get_user_by_email(login_data['email'])

        if not user_data:
            return jsonify({'error': 'User not found'}), 404

        if not bcrypt.verify(login_data['password'], user_data['_source']['password']):
            return jsonify({'error': 'Incorrect password'}), 401

        print(user_data)

        access_token = create_access_token(identity=str(user_data['_id']))

        response_data = {
            'user_id': str(user_data['_id']),
            'name': user_data['_source']['name'],
            'lastname': user_data['_source']['lastname'],
            'email': user_data['_source']['email'],
            'access_token': access_token,
            'message': 'Login successful'
        }

        return jsonify(response_data), 200

    def check_email_exists(self, email):
        query = {
            'query': {
                'term': {'email.keyword': email}
            }
        }

        search_results = scan(self.es, index='users', query=query)

        return any(search_results)

    def get_user_by_email(self, email):
        query = {
            'query': {
                'term': {'email.keyword': email}
            }
        }

        search_results = scan(self.es, index='users', query=query)

        user_data = next(search_results, None)

        return user_data if user_data else None
        
        
