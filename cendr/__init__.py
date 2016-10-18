from flask import Flask, g
from flask_restful import Api
from flask_debugtoolbar import DebugToolbarExtension
from datetime import date
from flask.ext.cache import Cache
from jinja2 import contextfilter
import json
import os

# Caching
app = Flask(__name__, static_url_path='/static')

with app.app_context():
    def get_ds():
        if not hasattr(g, 'ds'):
            from gcloud import datastore
            g.ds = datastore.Client(project="andersen-lab")
        return g.ds

    def get_google_sheet():
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



# Cache
if (os.getenv('SERVER_SOFTWARE') and
            os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    cache = Cache(app, config={'CACHE_TYPE': 'gaememcached'})
else:
    cache = Cache(app, config={'CACHE_TYPE': 'simple'})

api = Api(app)
build = "20160408"
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['version'] = "1.0.1"


if os.getenv('SERVER_SOFTWARE') and \
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/'):
    app.debug = False
    from flask_sslify import SSLify
    sslify = SSLify(app, skips=['strains/global-strain-map', '.well-known', '/.well-known'])
else:
    app.debug = True
    app.config['SECRET_KEY'] = "test"
    toolbar = DebugToolbarExtension(app)

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
#
# Custom Filters
#

@app.template_filter('comma')
def comma_filter(value):
    return "{:,.0f}".format(value)

from views import *
from cegwas import *