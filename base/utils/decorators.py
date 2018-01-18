import werkzeug
from functools import wraps
from flask import request, jsonify


def jsonify_request(func):
    """
        API function -
            Checks to see if there is a request and if
            there is, returns JSON of result.
    """
    @wraps(func)
    def jsonify_the_request(*args, **kwargs):
        as_list = kwargs.get("as_list")
        if 'as_list' in kwargs:
            kwargs.pop("as_list")
        if request.path.startswith("/api") and not as_list:
            return jsonify(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    return jsonify_the_request
