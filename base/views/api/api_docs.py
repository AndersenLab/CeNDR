from base.application import app
from flask import send_from_directory


@app.route("/data/api/docs/")
@app.route("/data/api/docs/<path:path>")
def docs(path="index.html"):
    print(path)
    return send_from_directory('../cendr-api-docs/docs/', path)
