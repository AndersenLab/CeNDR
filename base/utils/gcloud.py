from gcloud import datastore, storage


def google_datastore():
    """
        Fetch google datastore credentials
    """
    return datastore.Client(project='andersen-lab')


def store_item(kind, name, **kwargs):
    ds = google_datastore()
    m = datastore.Entity(key=ds.key(kind, name))
    for key, value in kwargs.items():
        if type(value) == str:
            m[key] = unicode(value)
        else:
            m[key] = value
    ds.put(m)


def query_item(kind, filters=None, projection=()):
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
        returns item by kind and name
    """
    ds = google_datastore()
    result = ds.get(ds.key(kind, name))
    return {k:v for k,v in result.items() if v}



def google_storage():
    """
        Fetch google storage credentials
    """
    return storage.Client(project='andersen-lab')


def get_releases():
    """
        Returns the set of releases
        stored in the elegansvariation.org/releases bucket
    """
    