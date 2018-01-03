from base.application import (get_ds,
                              cache,
                              add_to_order_ws,
                              lookup_order,
                              send_mail)
from flask import render_template, request, url_for, redirect, Response, abort
from base.models2 import strain_m
import yaml
from base.emails import order_submission
from datetime import datetime
from requests import post
import pytz
import hashlib
from flask import Blueprint
from base.views.api.api_strain import get_isotypes, query_strains
from base.utils.data_utils import dump_json
from collections import defaultdict
from logzero import logger

strain_bp = Blueprint('strain',
                       __name__,
                      template_folder='strain')


#
# Global Strain Map
#

@strain_bp.route('/')
def strain():
    """
        Redirect base route to the global strain map
    """
    return redirect(url_for('strain.map_page'))


@strain_bp.route('/global-strain-map/')
@cache.memoize(50)
def map_page():
    """
        Global strain map shows the locations of all wild isolates
        within the SQLite database.
    """
    VARS = {'title': "Global Strain Map",
            'strain_listing': dump_json(get_isotypes(known_origin=True))}
    return render_template('strain/global_strain_map.html', **VARS)


#
# Strain Data
#


@strain_bp.route('/strain_data.tsv')
def strain_metadata():
    """
        Dumps strain dataset; Normalizes lat/lon on the way out.
    """
    col_list = list(strain_m.__mapper__.columns)
    def generate():
        first = True
        if first:
            first = False
            header = [x.name for x in list(strain_m.__mapper__.columns)]
            yield ('\t'.join(header) + "\n").encode('utf-8')
        for row in query_strains():
            row = [getattr(row, column.name) for column in col_list]
            yield ('\t'.join(map(str, row)) + "\n").encode('utf-8')
    return Response(generate(), mimetype="text/tab-separated-values")


#
# Isotype View
#

@strain_bp.route('/isotype/<isotype_name>/')
@cache.memoize(50)
def isotype_page(isotype_name):
    isotype = query_strains(isotype_name = isotype_name)
    VARS = {"title": isotype_name,
            "isotype": isotype,
            "isotype_name": isotype_name,
            "reference_strain": [x for x in isotype if x.reference_strain][0],
            "strain_json_output": dump_json(isotype)}
    return render_template('strain/strain.html', **VARS)


#
# Strain Catalog
#

@strain_bp.route('/catalog')
@cache.memoize(50)
def strain_catalog():
    title = "Strain Catalog"
    VARS = {"title": "Strain Catalog",
            "warning": request.args.get('warning'),
            "strain_listing": query_strains()}
    return render_template('strain/strain_catalog.html', **VARS)

#
# Strain Submission
#


@strain_bp.route('/submit/')
def strain_submission_page():
    """
        Google form for submitting strains
    """
    title = "Strain Submission"
    return render_template('strain/strain_submission.html', **locals())


#
# Protocols
#

@strain_bp.route("/protocols/")
@cache.cached(timeout=50)
def protocols():
    title = "Protocols"
    protocols = yaml.load(
        open("base/static/yaml/protocols.yaml", 'r'))
    return render_template('protocols.html', **locals())


#
# Strain Ordering Pages
#
def calculate_total(item_list):
    item_price_list = {}
    for i in sorted(item_list):
        if i == "set_divergent":
            item_price_list[i] = 160
        elif i.startswith("set"):
            item_price_list[i] = 640
        else:
            item_price_list[i] = 15
    return item_price_list


@strain_bp.route('/order', methods=['GET', 'POST'])
def order_page():
    title = "Order"
    items = request.form.getlist("item")
    # Retreive SKU's for prices
    items = calculate_total(items)
    total = sum(items.values())
    strain_listing = list(set(request.form.getlist('item')))
    if not strain_listing:
        return redirect(url_for("strain.strain_catalog"))
    if request.method == 'POST':
        field_list = ['name', 'phone', 'email', 'shipping_service', 'address']
        warning = None
        captcha_passed = False
        if 'g-recaptcha-response' in request.form:
            resp = post('https://www.google.com/recaptcha/api/siteverify',
                          data = {'secret' : app.config['RECAPTCHA_SECRET_KEY'],
                                  'response' : request.form['g-recaptcha-response']})
            if resp.json()['success']:
                captcha_passed = True
            else:
                captcha_passed = False
                warning = "Failed to pass captcha"
            if 'shipping_service' in request.form and captcha_passed:
                # Check that all pieces are filled out.
                missing_fields = []
                for i in field_list:
                    if i in request.form:
                        if not request.form[i]:
                            missing_fields.append(i)
                            warning = "Missing Some Fields"
                if request.form['shipping_service'] in ['UPS','FEDEX'] and not request.form['shipping_account']:
                    warning = "No shipping account provided for " + request.form['shipping_service']
                if len(missing_fields) == 0 and warning is None:
                    ds = get_ds()
                    o = ds.get(ds.key("cendr-order", "count"))
                    
                    o["order-number"] += 1
                    ds.put(o)
                    order = {}
                    for k in field_list:
                        order[k] = request.form[k]
                    order['items'] = '\n'.join(
                        sorted([u"{k}:{v}".format(k=k, v=v) for k, v in items.items()]))
                    order['shipping_service'] = request.form['shipping_service']
                    order['shipping_account'] = request.form['shipping_account']
                    order['total'] = total
                    shipping = ""
                    if order['shipping_service'] == '$65 Flat Fee':
                        order['total'] += 65
                        shipping = "\nShipping\n=========\n$65"
                    order['date'] = datetime.now(pytz.timezone("America/Chicago"))
                    order['order_number'] = o['order-number']
                    order['is_donation'] = False
                    order['date'] = datetime.now(pytz.timezone(
                        "America/Chicago")).date().isoformat()
                    order['invoice_hash'] = hashlib.sha1(str(order)).hexdigest()[0:10]
                    order["url"] = "https://elegansvariation.org/order/" + \
                        order["invoice_hash"]
                    send_mail({"from": "no-reply@elegansvariation.org",
                               "to": [order["email"]],
                               "cc": ['dec@u.northwestern.edu',
                                      'robyn.tanny@northwestern.edu',
                                      'erik.andersen@northwestern.edu',
                                      'g-gilmore@northwestern.edu',
                                      'irina.iacobut@northwestern.edu'],
                               "subject": "CeNDR Order #" + str(order["order_number"]),
                               "text": order_submission.format(invoice_hash=order['invoice_hash'],
                                                               name=order['name'],
                                                               address=order[
                                                                   'address'],
                                                               items=order['items'],
                                                               total=order['total'],
                                                               date=order['date'],
                                                               shipping=shipping)})

                    # Save to google sheet
                    add_to_order_ws(order)

                    return redirect(url_for("order_confirmation", invoice_hash=order['invoice_hash']), code=302)

    return render_template('order.html', **locals())


@strain_bp.route("/order/<invoice_hash>/")
def order_confirmation(invoice_hash):
    order = lookup_order(invoice_hash)
    if order:
        order["items"] = {x.split(":")[0]: float(x.split(":")[1])
                          for x in order['items'].split("\n")}
        if order is None:
            abort(404)
        page_title = "Invoice Number: " + str(order['order_number'])
        return render_template('order_confirm.html', **locals())
    else:
        abort(404)
