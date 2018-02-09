import os
import json
import yaml
from flask import Flask, render_template, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from base.utils.data_utils import json_encoder
from base.utils.text_utils import render_markdown
from base.constants import CENDR_VERSION, APP_CONFIG

# Create
app = Flask(__name__,
            static_url_path='/static')

# Configuration - First load non-sensitive configuration info
app.config['json_encoder'] = json_encoder

# Load Credentials
# (BASE_VARS are the same regardless of whether we are debugging or in production)
BASE_VARS = yaml.load(open("env_config/base.yaml").read())
APP_CONFIG_VARS = yaml.load(open(f"env_config/{APP_CONFIG}.yaml").read())

app.config.update(BASE_VARS)
app.config.update(APP_CONFIG_VARS)
print(app.config)

# Setup cache
cache = Cache(app, config=app.config['CACHE'])

# Database
db_2 = SQLAlchemy(app)

# Set the json_encoder
app.json_encoder = json_encoder

biotypes = {
    "miRNA" : "microRNA",
    "piRNA" : "piwi-interacting RNA",
    "rRNA"  : "ribosomal RNA",
    "siRNA" : "small interfering RNA",
    "snRNA" : "small nuclear RNA",
    "snoRNA": "small nucleolar RNA",
    "tRNA"  : "transfer RNA",
    "vaultRNA" : "Short non-coding RNA genes that form part of the vault ribonucleoprotein complex",
    "lncRNA" : "Long non-coding RNA",
    "lincRNA" : "Long interspersed ncRNA",
    "pseudogene" : "non-functional gene.",
    "asRNA" : "Anti-sense RNA",
    "ncRNA" : "Non-coding RNA",
    "scRNA" : "Small cytoplasmic RNA"
}


def autoconvert(s):
    for fn in (int, float):
        try:
            return fn(s)
        except ValueError:
            pass
    return s



if app.config['DEBUG'] is False:
    from flask_sslify import SSLify
    # Ignore leading slash of urls; skips must use start of path
    sslify = SSLify(app, skips=['strains/global-strain-map',
                                'cronmapping'])
else:
    # Running locally
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    app.debug = True
    app.config["debug"] = True
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
app.register_blueprint(mapping_bp, url_prefix='/mapping')

# Main Pages - Homepage, Outreach, Contact
from base.views.primary import primary_bp
app.register_blueprint(primary_bp, url_prefix='')

# User Pages
from base.views.user import user_bp
app.register_blueprint(user_bp, url_prefix='/user')

# Authentication
from base.auth import *

# Inject globals
@app.context_processor
def inject():
    """
        Used to inject variables that
        need to be accessed globally
    """
    return dict(version=CENDR_VERSION,
                json=json,
                gs_static=gs_static,
                render_markdown=render_markdown)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


from base.views.api import *
from base.manage import (init_db)
