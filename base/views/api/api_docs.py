#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Handles redirecting the user to the API Documentation.

"""
from base.application import app
from flask import send_from_directory

@app.route("/data/api/docs/")
@app.route("/data/api/docs/<path:path>")
def docs(path="index.html"):
    return send_from_directory('../cendr-api-docs/docs/', path)
