import time
from flask import jsonify, Blueprint
from base.utils.cache import delete_expired_cache

maintenance_bp = Blueprint('maintenance',
                     __name__)


@maintenance_bp.route('/cleanup_cache', methods=['POST'])
def cleanup_cache():
  result = delete_expired_cache()
  response = jsonify({"result": result})
  response.status_code = 200
  return response
