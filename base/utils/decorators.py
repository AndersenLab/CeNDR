import arrow
from rich.console import Console
from functools import wraps
from flask import request, jsonify

console = Console()

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
        if request:
            is_tsv = request.args.get('output') == 'tsv'
            if request.endpoint.endswith(func.__name__) and not is_tsv:
                return jsonify(func(*args, **kwargs))
        return func(*args, **kwargs)
    return jsonify_the_request


def timeit(method):
  def timed(*args, **kw):
    start = arrow.utcnow()
    result = method(*args, **kw)
    diff = int((arrow.utcnow() - start).total_seconds())
    console.log(f"{diff} seconds")
    return result
  return timed