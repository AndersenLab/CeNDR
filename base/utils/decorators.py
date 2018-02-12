import werkzeug
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
        """
            Wraps API functions

            If you provide an 'as_python' = True
            argument, the response will be a python object
            and the as_python argument will be discarded.
        """
        if func.__name__ == request.endpoint:
            return jsonify(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    return jsonify_the_request
