# -*- coding: utf-8 -*-
import re
import datetime
from base.utils.data_utils import json_encoder
from base.utils.gcloud import get_item

recaptcha = get_item("credential", "recaptcha")


class base_config(object):
    VERSION = re.search("VERSION=version-(.*)\n", open(".travis.yml", 'r').read()) \
                .group(1) \
                .replace('-', '.')

    json_encoder = json_encoder
    RECAPTCHA_PUBLIC_KEY = recaptcha.get("RECAPTCHA_PUBLIC_KEY")
    RECAPTCHA_PRIVATE_KEY = recaptcha.get("RECAPTCHA_PRIVATE_KEY")
    SECRET_KEY = recaptcha.get("RECAPTCHA_PRIVATE_KEY")
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cendr.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class local(base_config):
    SQLALCHEMY_ECHO=False
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
    CC_EMAILS = ["danielecook@gmail.com"]



class production(base_config):
    CC_EMAILS = ['dec@u.northwestern.edu',
                 'robyn.tanny@northwestern.edu',
                 'erik.andersen@northwestern.edu',
                 'g-gilmore@northwestern.edu',
                 'irina.iacobut@northwestern.edu']