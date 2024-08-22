from flask import request, Blueprint
from controllers.student_controller import StudentController

student_routes = Blueprint('student', __name__)
student_controller = StudentController()

@student_routes.route('/student', methods=['POST'])
def create_student():
    return student_controller.create_student(request)

@student_routes.route('/student/<id>', methods=['GET'])
def get_student(id):
    return student_controller.get_student(id)

@student_routes.route('/student/<id>', methods=['PUT'])
def update_student(id):
    return student_controller.update_student(request, id)

@student_routes.route('/student/<id>', methods=['DELETE'])  
def delete_student(id):
    return student_controller.delete_student(id)

@student_routes.route('/student/search', methods=['GET'])
def search_student():
    return student_controller.search_student(request)

@student_routes.route('/student/extract_triplets', methods=['POST'])
def exctrat_triplets():
    return student_controller.exctrat_triplets(request)