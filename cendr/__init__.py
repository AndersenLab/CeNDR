import json
import os
import time
import re
import requests
import decimal
from flask import Flask, g
from peewee import *
from flask_restful import Api
from flask_debugtoolbar import DebugToolbarExtension
from datetime import date
from flask_caching import Cache
from gcloud import datastore

# Caching
app = Flask(__name__, static_url_path='/static')
app.config['TEMPLATES_AUTO_RELOAD'] = True
dbname = "cegwas_v2" # don't remove, imported elsewhere.

releases = ["20170531",
            "20160408"]

app.config['CURRENT_RELEASE'] = releases[0]



def get_vcf(release = releases[0]):
    return "http://storage.googleapis.com/elegansvariation.org/releases/{release}/WI.{release}.vcf.gz".format(release=release)


def get_ds():
    with app.app_context():
        if not hasattr(g, 'ds'):
            g.ds = datastore.Client(project="andersen-lab")
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


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, date):
        serial = obj.isoformat()
        return serial
    if type(obj) == decimal.Decimal:
        return float(obj)
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
    sslify = SSLify(app, skips=['strains/global-strain-map',
                                '.well-known',
                                'cronmapping'])
else:
    # Running locally
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})
    app.debug = True
    app.config["debug"] = True
    app.config['SECRET_KEY'] = "test"
    toolbar = DebugToolbarExtension(app)


version = re.search("VERSION=version-(.*)\n", open(".travis.yml", 'r').read()) \
            .group(1) \
            .replace('-', '.')

app.config['VERSION'] = version
app.config['TEMPLATE_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False


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



#
# Custom Filters
#

@app.template_filter('comma')
def comma_filter(value):
    return "{:,.0f}".format(value)


@app.template_filter('format_release')
def format_release_filter(value):
    return datetime.strptime(str(value), '%Y%m%d').strftime('%Y-%m-%d')

from cendr.task import *
from cendr.views import *
from cendr.views.api import *
from cendr.cegwas import *
