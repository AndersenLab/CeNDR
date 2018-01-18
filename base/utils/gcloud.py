import json
from flask import g
from gcloud import datastore, storage


def google_datastore():
    """
        Fetch google datastore credentials
    """
    if not hasattr(g, 'ds'):
        g.ds = datastore.Client(project='andersen-lab')
    return g.ds


def store_item(kind, name, **kwargs):
    ds = google_datastore()
    m = datastore.Entity(key=ds.key(kind, name))
    for key, value in kwargs.items():
        if type(value) == dict:
            m[key] = 'JSON:' + json.dumps(value)
        else:
            m[key] = value
    ds.put(m)


def query_item(kind, filters=None, projection=()):
    """
        Filter items from google datastore using a query
    """
    # filters:
    # [("var_name", "=", 1)]
    ds = google_datastore()
    query = ds.query(kind=kind, projection=projection)
    if filters:
        for var, op, val in filters:
            query.add_filter(var, op, val)
    return query.fetch()


def get_item(kind, name):
    """
        returns item by kind and name from google datastore
    """
    ds = google_datastore()
    result = ds.get(ds.key(kind, name))
    try:
        result_out = {}
        for k, v in result.items():
            if v.startswith("JSON:"):
                result_out[k] = json.loads(v[5:])
            elif v:
                result_out[k] = v
        return result_out
    except AttributeError:
        return None


def google_storage():
    """
        Fetch google storage credentials
    """
    return storage.Client(project='andersen-lab')

