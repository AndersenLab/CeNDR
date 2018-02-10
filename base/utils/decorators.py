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
        """
            Wraps API functions

            If you provide an 'as_python' = True
            argument, the response will be a python object
            and the as_python argument will be discarded.
        """
        as_python = kwargs.get("as_python")
        as_tsv = request.args.get('output') == 'tsv'
        if 'as_python' in kwargs:
            kwargs.pop('as_python')
        if request.path.startswith("/api") and not as_python and not as_tsv:
            return jsonify(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    return jsonify_the_request
