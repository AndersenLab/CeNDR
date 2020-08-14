import requests
from base.extensions import cache
from flask import Response, Blueprint

api_data_bp = Blueprint('api_data',
                     __name__,
                     template_folder='api')

@api_data_bp.route('/wormbase/<path:r>')
@cache.memoize(50)
def wormbase_api(r):
    r = requests.get('http://www.wormbase.org/rest/' + r, headers = {'Content-Type': 'application/json; charset=utf-8'}
)
    return Response(r.text, mimetype="text/json")
