from cendr import app, get_ds, cache, add_to_order_ws, lookup_order, send_mail
from cendr import json_serial
from flask import render_template, request, url_for, redirect, Response, abort
from cendr.models import strain
from collections import OrderedDict
import json
import yaml
from cendr.emails import order_submission
from datetime import datetime
import pytz
import hashlib


#
# Global Strain Map
#


@app.route('/strain/global-strain-map/')
@cache.memoize(50)
def map_page():
    title = "Global Strain Map"
    bcs = OrderedDict(
        [("Strain", url_for("strain_listing_page")), ("Global-Strain-Map", "")])
    strain_list_dicts = []
    strain_listing = list(strain.select().filter(strain.reference_strain == True)
                          .filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"]
                                 for x in strain_listing], default=json_serial)
    return render_template('map.html', **locals())


#
# Strain Data
#


@app.route('/strain/strain_data.tsv')
def strain_metadata():
    strain_listing = list(strain.select().filter(
        strain.isotype != None).tuples().execute())

    def generate():
        yield '\t'.join(strain._meta.sorted_field_names[1:21]) + "\n"
        for row in strain_listing:
            row = list(row)
            for k, f in enumerate(row):
                if type(f) == unicode:
                    row[k] = f.encode('utf-8', 'ignore')
            yield '\t'.join(map(str, row[1:21])) + "\n"
    return Response(generate(), mimetype="text/tab-separated-values")


#
# Isotype View
#

@app.route('/strain/<isotype_name>/')
@cache.memoize(50)
def isotype_page(isotype_name):
    page_title = isotype_name
    page_type = "isotype"
    obj = isotype_name
    rec = list(strain.filter(strain.isotype == isotype_name)
               .order_by(strain.latitude).dicts().execute())
    ref_strain = [x for x in rec if x["reference_strain"] == True][0]
    strain_json_output = json.dumps(
        [x for x in rec if x["latitude"] != None],  default=json_serial)
    return render_template('strain.html', **locals())


#
# Strain Catalog
#

@app.route('/strain/')
@cache.memoize(50)
def strain_listing_page():
    bcs = OrderedDict([("Strain", None)])
    title = "Strain Catalog"

    if 'warning' in request.args:
        warning = request.args["warning"]

    strain_listing = strain.select(strain.strain,
                                   strain.reference_strain,
                                   strain.isotype,
                                   strain.release,
                                   strain.previous_names,
                                   strain.set_1,
                                   strain.set_2,
                                   strain.set_3,
                                   strain.set_4,
                                   strain.set_divergent).filter(strain.isotype != None).order_by(strain.isotype).execute()
    return render_template('strain_catalog.html', **locals())

#
# Strain Submission
#


@app.route('/strain/submit/')
def strain_submission_page():
    bcs = OrderedDict(
        [("Strain", url_for("strain_listing_page")), ("Strain Submission", "")])
    title = "Strain Submission"
    return render_template('strain_submission.html', **locals())


#
# Protocols
#

@app.route("/strain/protocols/")
@cache.cached(timeout=50)
def protocols():
    title = "Protocols"
    bcs = OrderedDict(
        [("Strain", url_for("strain_listing_page")), ("Protocols", "")])
    protocols = yaml.load(
        open("cendr/static/content/data/protocols.yaml", 'r'))
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


@app.route('/order', methods=['GET', 'POST'])
def order_page():
    bcs = OrderedDict([("Strain", "/strain/"), ("Order", "")])
    title = "Order"
    strain_listing = list(set(request.form.getlist('item')))
    if (len(strain_listing) == 0):
        return redirect(url_for("strain_listing_page"))
    items = request.form.getlist("item")
    # Retreive SKU's for prices
    items = calculate_total(items)
    total = sum(items.values())
    field_list = ['name', 'phone', 'email', 'shipping_service', 'address']
    warning = None
    if 'shipping_service' in request.form:
        # Check that all pieces are filled out.
        missing_fields = []
        for i in field_list:
            if i in request.form:
                if not request.form[i]:
                    missing_fields.append(i)
                    warning = "Missing Some Fields"
        if request.form['shipping_service'] in ['UPS','FEDEX'] and not request.form['shipping_account']:
            warning = "No shipping account provided for " + request.form['shipping_service']
        print(warning)
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
            order["url"] = "http://elegansvariation.org/order/" + \
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


@app.route("/order/<invoice_hash>/")
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
