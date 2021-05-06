# Author: Daniel E. Cook
# Flask extensions
from flaskext.markdown import Markdown
from flask_caching import Cache
from flask_sslify import SSLify
from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager


sqlalchemy = SQLAlchemy()
markdown = Markdown
cache = Cache(config={'CACHE_TYPE': 'base.utils.cache.datastore_cache'})
sslify = SSLify
debug_toolbar = DebugToolbarExtension
jwt = JWTManager()
