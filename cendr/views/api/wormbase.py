from flask_restful import Resource
from cendr.models import strain
from cendr import app
from cendr import api
from flask import Response
from collections import OrderedDict
import requests

@app.route('/api/wormbase/<path:r>')
def wormbase_api(r):
    r = requests.get('http://www.wormbase.org/rest/' + r, headers = {'Content-Type': 'application/json; charset=utf-8'}
)
    return Response(r.text, mimetype="text/json")

