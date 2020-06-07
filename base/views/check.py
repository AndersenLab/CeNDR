# checks whether CeNDR is running successfully

from flask import jsonify, Blueprint

check_bp = Blueprint('check',
                     __name__)


@check_bp.route('/readiness_check')
def readiness_check():
    response = jsonify({'ready': True})
    response.status_code = 200
    return response

@check_bp.route('/liveliness_check')
def liveliness_check():
    response = jsonify({'ready': True})
    response.status_code = 200
    return response
