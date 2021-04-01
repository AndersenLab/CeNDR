#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

These functions will concern genetic data.

"""
import pickle
import base64
from cachelib import BaseCache
from base.utils.gcloud import get_item, store_item, delete_items_by_query
from time import time
from base.config import config

kind = config['DS_PREFIX'] + 'cache'

class DatastoreCache(BaseCache):
    def __init__(self, default_timeout=500):
        BaseCache.__init__(self, default_timeout)
        self.key_prefix = config["CENDR_VERSION"]

    def set(self, key, value, timeout=None):
        expires = time() + timeout
        try:
            value = base64.b64encode(pickle.dumps(value))
            store_item(kind, self.key_prefix + "/" + key, value=value, expires=expires, exclude_from_indexes=['value'])
            return True
        except:
            return False

    def get(self, key):
        try:
            item = get_item(kind, self.key_prefix + "/" + key)
            value = item.get('value')
            value = pickle.loads(base64.b64decode(value))
            expires = item.get('expires')
            if expires == 0 or expires > time():
                return value
        except AttributeError:
            return None

    def get_many(self, *keys):
        return [self.get(key) for key in keys]

    def get_dict(self, *keys):
        results = {}
        for key in keys:
            try:
                results.update({key: get_item(kind, key)})
            except AttributeError:
                pass
        return results

    def has(self, key):
        try:
            item = get_item(kind, key)
            expires = item.get('expires')
            if expires == 0 or expires > time():
                return True
        except:
            return False

    def set_many(self, mapping, timeout):
        for k, v in mapping.items():
            store_item(kind, k, value=v)


def datastore_cache(app, config, args, kwargs):
    return DatastoreCache(*args, **kwargs)


def delete_expired_cache():
    epoch_time = int(time())
    filters = [("expires", "<", epoch_time)]
    num_deleted = delete_items_by_query(kind, filters=filters, projection=['expires'])
    return num_deleted