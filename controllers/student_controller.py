from flask import jsonify;
from models.student import Student
import spacy;
from controllers.triplets_controller import TripletsController
from sentence_transformers import SentenceTransformer

class StudentController:
    def __init__(self):
        self.model = SentenceTransformer('all-mpnet-base-v2')


    def create_student(self, request):
        data = request.get_json()
        student = Student(**data)
        student.save()

        return jsonify(student.json())
    
    def get_student(self, id):
        student = Student.find_by_id(id)
        if student:
            return jsonify(student.json())
        else:
            return jsonify({"message": "Student not found"}), 404
    
    def update_student(self, request, id):
        data = request.get_json()
        student = Student.find_by_id(id)
        if student:
            student.update(data, id)
            return jsonify(student.json())
        else:
            return jsonify({"message": "Student not found"}), 404
    
    def delete_student(self, id):
        student = Student.find_by_id(id)
        if student:
            student.delete(id)
            return jsonify({"message": "Student deleted"})
        else:
            return jsonify({"message": "Student not found"}), 404
    
    def search_student(self, request):
        query = request.args.get("query")
        students = Student.search(query)
        return jsonify([student.json() for student in students])
    
    def exctrat_triplets(self, request):
        request_data = request.get_json()
        data = request_data['data']
        nlp = spacy.load('en_core_web_sm')
        doc = nlp(data)
        sentences_and_triplets = TripletsController.extract_triplets(self, doc.sents, 2 , 4)
        print(sentences_and_triplets)
        return jsonify(sentences_and_triplets)

    def calculate_and_save_vector(self, text):
        try:
            if not text:
                return None
            vector = self.model.encode(text)
            vector_list = vector.tolist()
            return vector_list
        except Exception as e:
            print(f"Error in calculate_and_save_vector: {e}")
            return None

