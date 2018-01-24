import json
from flask import g
from base.utils.data_utils import dump_json
from gcloud import datastore, storage
from logzero import logger


def google_datastore(open=False):
    """
        Fetch google datastore credentials

        Args:
            open - Return the client without storing it in the g object.
    """
    client = datastore.Client(project='andersen-lab')
    if open:
        return client
    if not hasattr(g, 'ds'):
        g.ds = client
    return g.ds


def store_item(kind, name, **kwargs):
    ds = google_datastore()
    exclude = kwargs.pop('exclude_from_indexes')
    if exclude:
        m = datastore.Entity(key=ds.key(kind, name), exclude_from_indexes=exclude)
    else:
        m = datastore.Entity(key=ds.key(kind, name))
    for key, value in kwargs.items():
        if isinstance(value, dict):
            m[key] = 'JSON:' + dump_json(value)
        else:
            m[key] = value
    ds.put(m)


def query_item(kind, filters=None, projection=(), order=None):
    """
        Filter items from google datastore using a query
    """
    # filters:
    # [("var_name", "=", 1)]
    ds = google_datastore()
    query = ds.query(kind=kind, projection=projection)
    if order:
        query.order = order
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
    logger.info(f"datastore: {kind} - {name}")
    try:
        result_out = {'_exists': True}
        for k, v in result.items():
            if isinstance(v, str) and v.startswith("JSON:"):
                result_out[k] = json.loads(v[5:])
                print(result_out)
            elif v:
                result_out[k] = v

        return result_out
    except AttributeError:
        return None


def google_storage(open=False):
    """
        Fetch google storage credentials
    """
    client = storage.Client(project='andersen-lab')
    if open:
        return client
    if not hasattr(g, 'gs'):
        g.gs = client
    return g.gs