import os
import json
import requests
from os.path import basename
from base.config import config
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from base.utils.text_utils import render_markdown
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException

from base.manage import (initdb,
                         update_strains,
                         update_credentials,
                         decrypt_credentials,
                         download_db)

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

# Tools
from base.views.tools import (tools_bp,
                              heritability_bp,
                              indel_primer_bp)

# Readiness and health checks
from base.views.check import check_bp

# API
from base.views.api.api_strain import api_strain_bp
from base.views.api.api_gene import api_gene_bp
from base.views.api.api_variant import api_variant_bp
from base.views.api.api_data import api_data_bp

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
from base.filters import (comma, format_release)


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
    configure_ssl(app)

    return app


def configure_ssl(app):
    """Configure SSL"""
    if os.getenv('HOME') == "/root":
        # Running on server
        app.debug = False
        # Ignore leading slash of urls; skips must use start of path
        sslify(app)
    elif app.config['DEBUG']:
        debug_toolbar(app)
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = True


def register_commands(app):
    """Register custom commands for the Flask CLI."""
    for command in [initdb,
                    update_strains,
                    update_credentials,
                    decrypt_credentials,
                    download_db]:
        app.cli.add_command(command)


def register_template_filters(app):
    for t_filter in [comma, format_release]:
        app.template_filter()(t_filter)


def register_extensions(app):
    markdown(app)
    cache.init_app(app, config={'CACHE_TYPE': 'base.utils.cache.datastore_cache'})
    sqlalchemy(app)
    CSRFProtect(app)
    app.config['csrf'] = CSRFProtect(app)


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
    
    # Tools
    app.register_blueprint(tools_bp, url_prefix='/tools')
    app.register_blueprint(heritability_bp, url_prefix='/tools')
    app.register_blueprint(indel_primer_bp, url_prefix='/tools')

    # API
    app.register_blueprint(api_strain_bp, url_prefix='/api')
    app.register_blueprint(api_gene_bp, url_prefix='/api')
    app.register_blueprint(api_variant_bp, url_prefix='/api')
    app.register_blueprint(api_data_bp, url_prefix='/api')

    # Auth
    app.register_blueprint(auth_bp, url_prefix='')
    app.register_blueprint(google_bp, url_prefix='/login')
    app.register_blueprint(github_bp, url_prefix='/login')

    # Healthchecks
    app.register_blueprint(check_bp, url_prefix='')


def gs_static(url, prefix='static'):
    return f"https://storage.googleapis.com/elegansvariation.org/{prefix}/{url}"


def configure_jinja(app):
    # Injects "contexts" into templates
    @app.context_processor
    def inject():
        return dict(version=os.environ.get("GAE_VERSION", "-9-9-9").split("-", 1)[1].replace("-", "."),
                    json=json,
                    list=list,
                    str=str,
                    int=int,
                    len=len,
                    gs_static=gs_static,
                    basename=basename,
                    render_markdown=render_markdown)


def register_errorhandlers(app):

    def render_error(e="generic"):
        return render_template("errors/%s.html" % e.code), e.code

    for e in [
        requests.codes.INTERNAL_SERVER_ERROR,
        requests.codes.NOT_FOUND,
        requests.codes.UNAUTHORIZED
    ]:
        app.errorhandler(e)(render_error)

    app.register_error_handler(HTTPException, render_error)
