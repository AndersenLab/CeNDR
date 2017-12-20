import yaml
import decimal
import datetime
from logzero import logger
from flask import g
from gcloud import storage
from sqlalchemy.ext.declarative import DeclarativeMeta
from flask import json


def load_yaml(yaml_file):
    return yaml.load(open(f"base/static/yaml/{yaml_file}", 'r'))


def get_gs():
    """
        Gets the elegansvariation.org google storage bucket which
        stores static assets and report data.
    """
    if not hasattr(g, 'gs'):
        g.gs = storage.Client(project='andersen-lab').get_bucket('elegansvariation.org')
    return g.gs


class json_encoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o.__class__, DeclarativeMeta):
            data = {}
            fields = o.__json__() if hasattr(o, '__json__') else dir(o)
            for field in [f for f in fields if not f.startswith('_') and f not in ['metadata', 'query', 'query_class']]:
                value = o.__getattribute__(field)
                try:
                    json.dumps(value)
                    data[field] = value
                except TypeError:
                    data[field] = None
            return data
        elif type(o) == decimal.Decimal:
            return float(o)
        elif isinstance(o, datetime.date):
            return str(o.isoformat())
        return json.JSONEncoder.default(self, o)

