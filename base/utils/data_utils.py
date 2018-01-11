#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
import yaml
import decimal
import pytz
import datetime
import hashlib
from datetime import datetime as dt
from flask import g
from gcloud import storage
from flask import json, request


def flatten_dict(d, max_depth=1):
    def expand(key, value):
        if hasattr(value, "__dict__"):
            value = value.__dict__
            print(value)
        if isinstance(value, dict) and max_depth > 0:
            return [ (key + '.' + k, v) for k, v in flatten_dict(value, max_depth - 1).items() ]
        else:
            return [ (key, value) ]

    items = [ item for k, v in d.items() for item in expand(k, v) ]

    return dict(items)


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
        if hasattr(o, "__dict__"):
            return {k: v for k,v in o.__dict__.items() if k != "id" and not k.startswith("_")}
        if type(o) == decimal.Decimal:
            return float(o)
        elif isinstance(o, datetime.date):
            return str(o.isoformat())
        return json.JSONEncoder.default(self, o)


def dump_json(data):
    """
        Use to dump json on internal requests.
    """
    return json.dumps(data, cls=json_encoder)


def sorted_files(path):
    """
        Sorts files
    """
    return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse=True)


def hash_it(object, length):
    return hashlib.sha1(str(hash(frozenset(object))).encode('utf-8')).hexdigest()[0:length]

def chicago_date():
    return dt.now(pytz.timezone("America/Chicago")).date().isoformat()
