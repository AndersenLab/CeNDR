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


class report_m(datastore_model):
    """
        The report model - for creating and retreiving
        information on reports
    """
    kind = 'report'
    def __init__(self, *args, **kwargs):
        super(report_m, self).__init__(*args, **kwargs)
        self.exclude_from_indexes = ('trait_data',)
        # Read trait data in upon initialization.
        if hasattr(self, 'trait_data'):
            self._trait_df = pd.read_csv(StringIO(self.trait_data), sep='\t')

    def trait_strain_count(self, trait_name):
        """
            Return number of strains submitted for a trait.
        """
        return self._trait_df[trait_name].dropna(how='any').count()

    def humanize(self):
        return arrow.get(self.created_on).humanize()

    def fetch_traits(self, trait_name=None, latest=True):
        """
            Fetches trait/task records associated with a report.

            Args:
                trait_name - Fetches a specific trait
                latest - Returns only the first record of each trait.

            Returns
                If a trait name is given, and latest - ONE result
                If latest - one result for each trait
                if neight - all tasks associated with a report.
        """
        report_filter = [('report_slug', '=', self.name)]
        if trait_name:
            trait_list = [trait_name]
        else:
            trait_list = self.trait_list
        result_out = []
        for trait in trait_list:
            trait_filters = report_filter + [('trait_name', '=', trait)]
            results = list(query_item('trait',
                                      filters=trait_filters,
                                      order=['report_slug', 'trait_name', '-created_on']))
            if results:
                if trait_name and latest:
                    result_out = trait_m(results[0].key.name)
                elif latest:
                    result_out.append(trait_m(results[0].key.name))
                else:
                    for result in results:
                        result_out.append(result)
        return result_out


class trait_m(datastore_model):
    """
        Class for storing data on tasks
        associated with a report.
    """
    kind = 'trait'

    def upload_files(self, file_list):
        """
            Used to upload files from pipeline to the
            reports bucket.

            Stores uploaded files.
        """
        gs = storage.Client(project='andersen-lab')
        cendr_bucket = gs.get_bucket("cendr")
        for fname in file_list:
            print(f"Uploading {fname} to {self.name}/{fname}")
            base_name = os.path.basename(fname)
            cendr_bucket.blob(f"{self.name}/{base_name}").upload_from_filename(fname)
        
        # Update self to store file list
        self.file_list = file_list

