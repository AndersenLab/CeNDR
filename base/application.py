import os
import json
import yaml
from os.path import basename
from flask import Flask, render_template, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from base.utils.data_utils import json_encoder
from base.utils.text_utils import render_markdown
from base.constants import CENDR_VERSION, APP_CONFIG
from flaskext.markdown import Markdown
from werkzeug.middleware.proxy_fix import ProxyFix


# Create
app = Flask(__name__,
            static_url_path='/static')

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# Add markdown
Markdown(app)

# Configuration - First load non-sensitive configuration info
app.config['json_encoder'] = json_encoder

# Load Credentials
# (BASE_VARS are the same regardless of whether we are debugging or in production)
BASE_VARS = yaml.load(open("env_config/base.yaml").read())
APP_CONFIG_VARS = yaml.load(open(f"env_config/{APP_CONFIG}.yaml").read())

app.config.update(BASE_VARS)
app.config.update(APP_CONFIG_VARS)

# Setup cache
cache = Cache(app, config={'CACHE_TYPE': 'base.utils.cache.datastore_cache'})

# Database
db_2 = SQLAlchemy(app)

# Set the json_encoder
app.json_encoder = json_encoder


def autoconvert(s):
    for fn in (int, float):
        try:
            return fn(s)
        except ValueError:
            pass
    return s


if os.getenv('HOME') == "/root":
    """
        Running on server
    """
    app.debug = False
    from flask_sslify import SSLify
    # Ignore leading slash of urls; skips must use start of path
    sslify = SSLify(app)
elif app.config['DEBUG']:
    app.debug = True
    #app.config["debug"] = True
    app.config['SECRET_KEY'] = "test"
    toolbar = DebugToolbarExtension(app)


def gs_static(url, prefix='static'):
    return f"https://storage.googleapis.com/elegansvariation.org/{prefix}/{url}"


# Template filters
from base.utils.template_filters import *

# About Pages
from base.views.about import about_bp
app.register_blueprint(about_bp, url_prefix='/about')

# Strain Pages
from base.views.strains import strain_bp
app.register_blueprint(strain_bp, url_prefix='/strain')

# Order Pages
from base.views.order import order_bp
app.register_blueprint(order_bp, url_prefix='/order')

# Data Pages
from base.views.data import data_bp
app.register_blueprint(data_bp, url_prefix='/data')

# Mapping Pages -
from base.views.mapping import mapping_bp
app.register_blueprint(mapping_bp, url_prefix='')

# Gene Pages
from base.views.gene import gene_bp
app.register_blueprint(gene_bp, url_prefix='/gene')

# Main Pages - Homepage, Outreach, Contact
from base.views.primary import primary_bp
app.register_blueprint(primary_bp, url_prefix='')

# User Pages
from base.views.user import user_bp
app.register_blueprint(user_bp, url_prefix='/user')

# Authentication
from base.auth import google_bp, github_bp
app.register_blueprint(google_bp, url_prefix='/login')
app.register_blueprint(github_bp, url_prefix='/login')


# Inject globals
@app.context_processor
def inject():
    """
        Used to inject variables that
        need to be accessed globally
    """
    return dict(version=CENDR_VERSION,
                json=json,
                list=list,
                str=str,
                int=int,
                len=len,
                gs_static=gs_static,
                basename=basename,
                render_markdown=render_markdown)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', page_title="Not found"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html', page_title="Not found"), 500


from base.views.api import *
from base.manage import (init_db)
