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
            and automatically jsonifies if
            its an API call
        """
        is_tsv = request.args.get('output') == 'tsv'
        if func.__name__ == request.endpoint and not is_tsv:
            return jsonify(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    return jsonify_the_request
