import yaml
from flask import g
from gcloud import storage


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