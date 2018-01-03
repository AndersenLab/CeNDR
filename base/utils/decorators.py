from functools import wraps
from flask import request, jsonify
from logzero import logger


def jsonify_request(func):
    """
        API function - 
            Checks to see if there is a request and if
            there is, returns JSON of result.
    """
    @wraps(func)
    def jsonify_the_request(*args, **kwargs):
        logger.info(request.path)
        if request.path.startswith("/api"):
            return jsonify(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    return jsonify_the_request
