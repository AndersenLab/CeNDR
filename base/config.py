# -*- coding: utf-8 -*-
import datetime


class base_config(object):
	pass


class local(base_config):
    ADDRESS = "http://localhost:5000"
    JSON_SORT_KEYS = True
    DEBUG = True
    SESSION_COOKIE_PATH='/'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_NAME = 'cendr'
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(31)