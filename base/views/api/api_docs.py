from base.models import strain
from base.models2 import strain_m
from base.application import app
from base.utils.decorators import jsonify_request
from flask import send_from_directory


@app.route("/data/api/docs/")
@app.route("/data/api/docs/<path:path>")
def docs(path="index.html"):
    print(path)
    return send_from_directory('../docs/build/', path)
