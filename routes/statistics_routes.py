

from flask import request, Blueprint
from controllers.statistics_controller import StatisticsController
from flask_jwt_extended import jwt_required

statistics_routes = Blueprint('statistics', __name__)

statistics_controller = StatisticsController()

@statistics_routes.route('/statistics', methods=['GET'])
@jwt_required()
def get_statistics():
    return statistics_controller.get_index_counts()