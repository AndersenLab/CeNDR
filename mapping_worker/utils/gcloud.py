#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Utility functions for running the task

"""
import os
import arrow
import json
import pandas as pd
from io import StringIO
from gcloud import datastore, storage
from logzero import logger


def get_item(kind, name):
    """
        returns item by kind and name from google datastore
    """
    ds = datastore.Client(project='andersen-lab')
    result = ds.get(ds.key(kind, name))
    try:
        result_out = {'_exists': True}
        for k, v in result.items():
            if isinstance(v, str) and v.startswith("JSON:"):
                result_out[k] = json.loads(v[5:])
            elif v:
                result_out[k] = v

        return result_out
    except AttributeError:
        return None


def store_item(kind, name, **kwargs):
    ds = datastore.Client(project='andersen-lab')
    exclude = kwargs.pop('exclude_from_indexes')
    if exclude:
        m = datastore.Entity(key=ds.key(kind, name), exclude_from_indexes=exclude)
    else:
        m = datastore.Entity(key=ds.key(kind, name))
    for key, value in kwargs.items():
        if isinstance(value, dict):
            m[key] = 'JSON:' + json.dumps(value)
        else:
            m[key] = value
    ds.put(m)


def query_item(kind, filters=None, projection=(), order=None):
    """
        Filter items from google datastore using a query
    """
    # filters:
    # [("var_name", "=", 1)]
    ds = datastore.Client(project='andersen-lab')
    query = ds.query(kind=kind, projection=projection)
    if order:
        query.order = order
    if filters:
        for var, op, val in filters:
            query.add_filter(var, op, val)
    return query.fetch()


class datastore_model(object):
    """
        Base datastore model

        Google datastore is used to store dynamic information
        such as users and reports.

        Note that the 'kind' must be defined within sub
    """

    def __init__(self, name):
        self.name = name
        self.exclude_from_indexes = None
        item = get_item(self.kind, name)
        if item:
            self._exists = True
            self.__dict__.update(item)
        else:
            self._exists = False

    def save(self):
        self._exists = True
        item_data = {k: v for k, v in self.__dict__.items() if k not in ['kind', 'name'] and not k.startswith("_")}
        store_item(self.kind, self.name, **item_data)

    def __repr__(self):
        return f"<{self.kind}:{self.name}>"


class trait_m(datastore_model):
    """
        Trait class corresponds to a trait analysis within a report.
        This class contains methods for submitting jobs and fetching results
        for an analysis.

        If a task is re-run the report will only display the latest version.
    """
    kind = 'trait'

    def __init__(self, *args, **kwargs):
        """
            The trait_m object adopts the task
            ID assigned by AWS Fargate.
        """
        super(trait_m, self).__init__(*args, **kwargs)
        self.exclude_from_indexes = ['trait_data', 'error_traceback', 'CEGWAS_VERSION', 'task_info']


    def upload_files(self, file_list):
        """
            Used to upload files from pipeline to the
            reports bucket.

            Stores uploaded files.
        """
        gs = storage.Client(project='andersen-lab')
        cendr_bucket = gs.get_bucket("elegansvariation.org")
        for fname in file_list:
            base_name = os.path.basename(fname)
            report_base = f"reports/{self.REPORT_VERSION}/{self.name}/{base_name}"
            print(f"Uploading {fname} to {report_base}")
            cendr_bucket.blob(report_base).upload_from_filename(fname)
        
        # Update self to store file list
        self.file_list = file_list


class mapping_m(datastore_model):
    """
        The mapping/peak interval model
    """
    kind = 'mapping'
    def __init__(self, *args, **kwargs):
        super(mapping_m, self).__init__(*args, **kwargs)
