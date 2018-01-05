import json
import os
import time
import requests
from peewee import *
from base import config
from flask import Flask, g
from flask_debugtoolbar import DebugToolbarExtension
from flask_caching import Cache
from gcloud import datastore
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from base.utils.data_utils import json_encoder
from base.utils.gcloud import google_datastore


# Caching
app = Flask(__name__, static_url_path='/static')
app.config.from_object(getattr(config, os.environ['APP_CONFIG']))

# Setup cache
cache = Cache(app, config=app.config['CACHE'])

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cendr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db_2 = SQLAlchemy(app)

# json encoder
app.json_encoder = json_encoder


dbname = "cegwas_v2" # don't remove, imported elsewhere.

releases = ["20170531",
            "20160408"]

app.config['CURRENT_RELEASE'] = releases[0]


def get_vcf(release = releases[0]):
    return "http://storage.googleapis.com/elegansvariation.org/releases/{release}/WI.{release}.vcf.gz".format(release=release)


def get_ds():
    with app.app_context():
        if not hasattr(g, 'ds'):
            g.ds = google_datastore()
        return g.ds


ds = get_ds()

# recaptcha
app.config.update(dict(ds.get(ds.key('credential', 'recaptcha'))))

credentials = dict(ds.get(ds.key("credential", 'cegwas-data')))
db = MySQLDatabase(dbname, **credentials)

@app.before_request
def _db_connect():
    try:
        db.connect()
    except:
        time.sleep(1)
        db.connect()


@app.teardown_request
def _db_close(exc):
    if not db.is_closed():
        db.close()


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



if os.getenv('HOME') == "/root":
    # Running on server
    # cache = Cache(app, config={'CACHE_TYPE': 'gaememcached'})
    # Cache service not yet available - use simple for now.
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    app.debug = False
    app.config["debug"] = False
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


def get_google_order_sheet():
    with app.app_context():
        if not hasattr(g, 'gc'):
            import gspread
            from oauth2client.service_account import ServiceAccountCredentials
            ds = get_ds()
            sa = ds.get(ds.key("credential", "service_account"))
            sa = json.loads(sa["json"])
            scope = ['https://spreadsheets.google.com/feeds']
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(sa, scope)
            gc = gspread.authorize(credentials)
            g.gc = gc
        return gc.open_by_key("1BCnmdJNRjQR3Bx8fMjD_IlTzmh3o7yj8ZQXTkk6tTXM").worksheet("orders")


def add_to_order_ws(row):
    """
        Stores order info in a google sheet.
    """
    ws = get_google_order_sheet()
    index = sum([1 for x in ws.col_values(1) if x]) + 1

    header_row = filter(len, ws.row_values(1))
    values = []
    for x in header_row:
        if x in row.keys():
            values.append(row[x])
        else:
            values.append("")

    row = map(str, row)
    ws.insert_row(values, index)


def lookup_order(invoice_hash):
    ws = get_google_order_sheet()
    find_row = ws.findall(invoice_hash)
    if len(find_row) > 0:
        row = ws.row_values(find_row[0].row)
        header_row = ws.row_values(1)
        result = dict(zip(header_row, row))
        return {k:v for k,v in result.items() if v}
    else:
        return None


def send_mail(data):
    ds = get_ds()
    api_key = ds.get(ds.key("credential", 'mailgun'))['apiKey']
    return requests.post(
        "https://api.mailgun.net/v3/mail.elegansvariation.org/messages",
        auth=("api", api_key),
        data=data)


def gs_static(url, prefix='static'):
    return f"https://storage.googleapis.com/elegansvariation.org/{prefix}/{url}"

# Inject globals
@app.context_processor
def inject():
    return dict(gs_static=gs_static)

# Template filters
from base.utils.template_filters import *

# About Pages
from base.views.about import about_bp
app.register_blueprint(about_bp, url_prefix='/about')

# Strain Pages
from base.views.strains import strain_bp
app.register_blueprint(strain_bp, url_prefix='/strain')

# Main Pages - Homepage, Outreach, Contact
from base.views.primary import primary_bp
app.register_blueprint(primary_bp, url_prefix='')





#from base.utils.auth import *
from base.task import *
from base.views import *
from base.views.api import *
from base.manage import (initdb)


print(app)
print(dir(app))