from flask import Flask, g
from peewee import *
from flask_restful import Api
from flask_debugtoolbar import DebugToolbarExtension
from datetime import date
from flask_cache import Cache
from jinja2 import contextfilter
import json
import yaml
import os
from gcloud import datastore
from playhouse.pool import PooledMySQLDatabase
import MySQLdb
import _mysql
import requests


# Caching
app = Flask(__name__, static_url_path='/static')
app.config['TEMPLATES_AUTO_RELOAD'] = True
dbname = "cegwas_v2" # don't remove, imported elsewhere.


releases = ["20170531",
            "20160408"]


def get_vcf(release = releases[0]):
    return "http://storage.googleapis.com/elegansvariation.org/releases/{release}/WI.{release}.vcf.gz".format(release=release)


def get_ds():
    with app.app_context():
        if not hasattr(g, 'ds'):
            g.ds = datastore.Client(project="andersen-lab")
        return g.ds

def get_google_sheet():
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
        return g.gc

ds = get_ds()


credentials = dict(ds.get(ds.key("credential", 'cegwas-data')))
db = PooledMySQLDatabase(dbname, stale_timeout=300, **credentials)

def get_db():
    return db

@app.before_request
def db_connect():
    g.db =  get_db()
    g.db.connect()

@app.teardown_request
def db_disconnect(exception):
    if hasattr(g, 'db'): g.db.close()


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


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, date):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


def autoconvert(s):
    for fn in (int, float):
        try:
            return fn(s)
        except ValueError:
            pass
    return s

class CustomEncoder(json.JSONEncoder):

    def default(self, o):
        if type(o) == decimal.Decimal:
            return float(o)
        if isinstance(o, datetime.date):
            return str(o)
        return super(CustomEncoder, self).default(o)

if os.getenv('HOME') == "/root":
    # Running on server
    # cache = Cache(app, config={'CACHE_TYPE': 'gaememcached'})
    # Cache service not yet available - use simple for now.
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    app.debug = False
    app.config["debug"] = False
    from flask_sslify import SSLify
    # Ignore leading slash of urls; skips must use start of path
    sslify = SSLify(app, skips=['strains/global-strain-map', '.well-known', 'cronmapping'])
else:
    # Running locally
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    app.debug = True
    app.config["debug"] = True
    app.config['SECRET_KEY'] = "test"
    toolbar = DebugToolbarExtension(app)


version = [x for x in yaml.load(open(".travis.yml", 'r').read())['before_install'] if 'VERSION' in x][0].split("=")[1]
app.config['version'] = version.split(".")[0].replace("-",".").replace("version.","")
app.config["TEMPLATE_AUTO_RELOAD"] = True
api = Api(app)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

def add_to_order_ws(row):
    """
        Stores order info in a google sheet.
    """
    gc = get_google_sheet()
    orders = gc.open_by_key("1BCnmdJNRjQR3Bx8fMjD_IlTzmh3o7yj8ZQXTkk6tTXM")
    ws = orders.worksheet("orders")
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
    gc = get_google_sheet()
    orders = gc.open_by_key("1BCnmdJNRjQR3Bx8fMjD_IlTzmh3o7yj8ZQXTkk6tTXM")
    ws = orders.worksheet("orders")
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



#
# Custom Filters
#

@app.template_filter('comma')
def comma_filter(value):
    return "{:,.0f}".format(value)


@app.template_filter('format_release')
def format_release_filter(value):
    return datetime.strptime(str(value), '%Y%m%d').strftime('%Y-%m-%d')

from task import *
from views import *
from cegwas import *
