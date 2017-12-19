# -*- coding: utf-8 -*-
import re
import datetime

class base_config(object):
	VERSION = re.search("VERSION=version-(.*)\n", open(".travis.yml", 'r').read()) \
                .group(1) \
                .replace('-', '.')


class local(base_config):
    ADDRESS = "http://localhost:5000"
    JSON_SORT_KEYS = True
    DEBUG = True
    SESSION_COOKIE_PATH='/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_NAME = 'cendr'
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(31)
    CACHE = {'CACHE_TYPE': 'filesystem',
             'CACHE_KEY_PREFIX': base_config.VERSION,
             'CACHE_DIR': '_cache'}
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    TEMPLATE_AUTO_RELOAD = True
