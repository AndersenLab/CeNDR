from flask import Flask
from flask_restful import Api
from flask_debugtoolbar import DebugToolbarExtension
from models import *
from datetime import date
from flask.ext.cache import Cache
from jinja2 import contextfilter
import json

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

# Caching
app = Flask(__name__, static_url_path='/static')

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
app.config['version'] = "1.0.0"


if os.getenv('SERVER_SOFTWARE') and \
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/'):
    app.debug = False
    from flask_sslify import SSLify
    sslify = SSLify(app, skips=['strains/global-strain-map'])
else:
    app.debug = True
    app.config['SECRET_KEY'] = "test"
    toolbar = DebugToolbarExtension(app)

def add_to_order_ws(row):
    """
        Stores order info in a google sheet.
    """
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    sa = ds.get(ds.key("credential", "service_account"))
    sa = json.loads(sa["json"])
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(sa, scope)
    gc = gspread.authorize(credentials)
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
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    sa = ds.get(ds.key("credential", "service_account"))
    sa = json.loads(sa["json"])
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(sa, scope)
    gc = gspread.authorize(credentials)
    orders = gc.open_by_key("1BCnmdJNRjQR3Bx8fMjD_IlTzmh3o7yj8ZQXTkk6tTXM")
    ws = orders.worksheet("orders")
    row = ws.row_values(ws.findall(invoice_hash)[0].row)
    header_row = ws.row_values(1)
    result = dict(zip(header_row, row))
    return {k:v for k,v in result.items() if v}
#
# Custom Filters
#

@app.template_filter('comma')
def comma_filter(value):
    return "{:,.0f}".format(value)

from views import *
from cegwas import *