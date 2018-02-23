from base.application import app, cache
from flask import Response
import requests

@app.route('/api/wormbase/<path:r>')
@cache.memoize(50)
def wormbase_api(r):
    r = requests.get('http://www.wormbase.org/rest/' + r, headers = {'Content-Type': 'application/json; charset=utf-8'}
)
    return Response(r.text, mimetype="text/json")
