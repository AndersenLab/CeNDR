# -*- coding: utf-8 -*-
import re
import datetime
from base.utils.data import json_encoder


class base_config(object):
    VERSION = re.search("VERSION=version-(.*)\n", open(".travis.yml", 'r').read()) \
                .group(1) \
                .replace('-', '.')

    json_encoder = json_encoder



class local(base_config):
    ADDRESS = "http://localhost:5000"
    JSON_SORT_KEYS = True
    DEBUG = True
    SESSION_COOKIE_PATH='/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_NAME = 'cendr'
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(31)
    CACHE = {'CACHE_TYPE': 'null',
             'CACHE_KEY_PREFIX': base_config.VERSION,
             'CACHE_DIR': '_cache'}
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    TEMPLATE_AUTO_RELOAD = True


class production(base_config):
    pass