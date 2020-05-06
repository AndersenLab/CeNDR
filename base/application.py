import os
import json
import requests
from os.path import basename
from base.config import config
from flask import Flask, render_template
from base.utils.text_utils import render_markdown
from werkzeug.middleware.proxy_fix import ProxyFix
from logzero import logger
from base.utils.data_utils import json_encoder

from base.manage import init_db

# --------- #
#  Routing  #
# --------- #
from base.views.about import about_bp
from base.views.primary import primary_bp
from base.views.strains import strain_bp
from base.views.order import order_bp
from base.views.data import data_bp
from base.views.mapping import mapping_bp
from base.views.gene import gene_bp
from base.views.user import user_bp
from base.views.tools import tools_bp

# API
from base.views.api.api_strain import api_strain_bp
from base.views.api.api_gene import api_gene_bp
from base.views.api.api_variant import api_variant_bp

# Auth
from base.auth import (auth_bp,
                       google_bp,
                       github_bp)

# ---- End Routing ---- #

# Extensions
from base.extensions import (markdown,
                             cache,
                             debug_toolbar,
                             sslify,
                             sqlalchemy)

# Template filters
from base.filters import (comma, format_release_filter)


def create_app(config=config):
    """Returns an initialized Flask application."""
    app = Flask(__name__,
                static_url_path='/static')

    # Fix wsgi proxy
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    app.config.update(config)

    register_commands(app)
    register_blueprints(app)
    register_template_filters(app)
    register_extensions(app)
    register_errorhandlers(app)
    configure_jinja(app)

    if os.getenv('HOME') == "/root":
        # Running on server
        app.debug = False
        # Ignore leading slash of urls; skips must use start of path
        sslify.init_app(app)
    elif app.config['DEBUG']:
        app.debug = True
        app.config['SECRET_KEY'] = "test"
        debug_toolbar(app)
    
    return app


def register_commands(app):
    """Register custom commands for the Flask CLI."""
    for command in [init_db]:
        app.cli.command()(command)


def register_template_filters(app):
    for t_filter in [comma, format_release_filter]:
        app.template_filter()(t_filter)


def register_extensions(app):
    markdown(app)
    cache.init_app(app, config={'CACHE_TYPE': 'base.utils.cache.datastore_cache'})
    sqlalchemy(app)


def register_blueprints(app):
    """Register blueprints with the Flask application."""
    app.register_blueprint(primary_bp, url_prefix='')
    app.register_blueprint(about_bp, url_prefix='/about')
    app.register_blueprint(strain_bp, url_prefix='/strain')
    app.register_blueprint(order_bp, url_prefix='/order')
    app.register_blueprint(data_bp, url_prefix='/data')
    app.register_blueprint(mapping_bp, url_prefix='')
    app.register_blueprint(gene_bp, url_prefix='/gene')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(tools_bp, url_prefix='/tools')

    # API
    app.register_blueprint(api_strain_bp, url_prefix='/api')
    app.register_blueprint(api_gene_bp, url_prefix='/api')
    app.register_blueprint(api_variant_bp, url_prefix='/api')

    # Auth
    app.register_blueprint(auth_bp, url_prefix='')
    app.register_blueprint(google_bp, url_prefix='/login')
    app.register_blueprint(github_bp, url_prefix='/login')


def gs_static(url, prefix='static'):
    return f"https://storage.googleapis.com/elegansvariation.org/{prefix}/{url}"


def configure_jinja(app):
    # Injects "contexts" into templates
    @app.context_processor
    def inject():
        return dict(json=json,
                    list=list,
                    str=str,
                    int=int,
                    len=len,
                    gs_static=gs_static,
                    basename=basename,
                    render_markdown=render_markdown)


def register_errorhandlers(app):

    def render_error(e):
        return render_template("errors/%s.html" % e.code), e.code

    for e in [
        requests.codes.INTERNAL_SERVER_ERROR,
        requests.codes.NOT_FOUND,
        requests.codes.UNAUTHORIZED
    ]:
        app.errorhandler(e)(render_error)