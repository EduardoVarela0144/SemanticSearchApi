from flask import request, Blueprint
from controllers.user_controller import UserController

user_routes = Blueprint('user', __name__)

user_controller = UserController()

@user_routes.route('/user/signin', methods=['POST'])
def sign_in():
    return user_controller.register_user(request)

@user_routes.route('/user/login', methods=['POST'])
def log_in():
    return user_controller.login_user(request)