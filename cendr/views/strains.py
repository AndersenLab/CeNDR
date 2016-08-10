from cendr import app, autoconvert, ds, db, cache
from cendr import json_serial
from flask import render_template, request, url_for, redirect, make_response, Response, abort
from cendr.models import strain
from collections import OrderedDict
import json
import os
import yaml
import stripe
try:
    from google.appengine.api import mail
except:
    pass # Importing this not always important...
from cendr.emails import order_submission
from gcloud.datastore.entity import Entity
from datetime import datetime
import pytz
from dateutil.relativedelta import relativedelta
#
# Global Strain Map
#


@app.route('/strain/global-strain-map/')
@cache.cached()
def map_page():
    title = "Global Strain Map"
    bcs = OrderedDict([("Strain", url_for("strain_listing_page")), ("Global-Strain-Map", "")])
    strain_list_dicts = []
    strain_listing = list(strain.select().filter(strain.reference_strain == True)
        .filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('map.html', **locals())


#
# Strain Metadata
#


@app.route('/strain/metadata.tsv')
def strain_metadata():
    strain_listing = list(strain.select().filter(
        strain.isotype != None).tuples().execute())
    def generate():
        yield '\t'.join(strain._meta.sorted_field_names[1:21]) + "\n"
        for row in strain_listing:
            row = list(row)
            for k, f in enumerate(row):
                if type(f) == unicode:
                    row[k] = f.encode('ascii', 'ignore')
            yield '\t'.join(map(str, row[1:21])) + "\n"
    return Response(generate(), mimetype="text/csv")



#
# Isotype View
#

@app.route('/strain/<isotype_name>/')
@cache.cached()
def isotype_page(isotype_name):
    page_title = isotype_name
    page_type = "isotype"
    obj = isotype_name
    rec = list(strain.filter(strain.isotype == isotype_name)
                .order_by(strain.latitude).dicts().execute())
    ref_strain = [x for x in rec if x["reference_strain"] == True][0]
    strain_json_output = json.dumps([x for x in rec if x["latitude"] != None],  default=json_serial)
    return render_template('strain.html', **locals())


#
# Strain Catalog
#

@app.route('/strain/')
@cache.cached()
def strain_listing_page():
    bcs = OrderedDict([("Strain", None)])
    title = "Strain Catalog"

    if 'warning' in request.args:
        warning = request.args["warning"]

    strain_listing = strain.select(strain.strain,
                                   strain.reference_strain,
                                   strain.isotype,
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
    bcs = OrderedDict([("Strain", url_for("strain_listing_page")), ("Strain Submission", "")])
    title = "Strain Submission"
    return render_template('strain_submission.html', **locals())


#
# Protocols
#

@app.route("/strain/protocols/")
def protocols():
    title = "Protocols"
    bcs = OrderedDict([("Strain", url_for("strain_listing_page")), ("Protocols", "")])
    protocols = yaml.load(open("cendr/static/content/data/protocols.yaml", 'r'))
    return render_template('protocols.html', **locals())



#
# Strain Ordering Pages
# 

def calculate_total(item_list):
    item_price_list = {}
    for i in item_list:
        if i == "set_divergent":
            item_price_list[i] = 10000
        elif i.startswith("set"):
            item_price_list[i] = 40000
        else:
            item_price_list[i] = 1000
    return item_price_list

@app.route('/order', methods=['GET','POST'])
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
    field_list = ['name', 'phone', 'email', 'shipping-account', 'address']
    print(request.form)
    if 'shipping-service' in request.form:
        # Check that all pieces are filled out.
        missing_fields = []
        for i in field_list:
            if i in request.form:
                if not request.form[i]:
                    missing_fields.append(i)
                    warning = "Missing Some Fields"
        if len(missing_fields) == 0:
            o = ds.get(ds.key("cendr-order", "count"))
            o["order-number"] += 1
            order = Entity(ds.key('cendr-order'))
            for k in field_list:
                order[k] = request.form[k]
            order["items"] = [u"{k}:{v}".format(k=k, v=v) for k,v in items.items()]
            order["total"] = total
            order['submitted'] = datetime.now(pytz.timezone("America/Chicago"))
            order['order-number'] = o['order-number']
            order['shipping-service'] = request.form['shipping-service']
            with ds.transaction():
                ds.put(o)
                ds.put(order)
            order_hash = order.key.id
            mail.send_mail(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
               to=order["email"],
               subject="CeNDR Order #" + str(order["order-number"]),
               body=order_submission.format(order_hash=order_hash))
            return redirect(url_for("order_confirmation", order_hash=order_hash), code=302)
        
    return render_template('order.html', **locals())

@app.route("/order/<order_hash>/")
def order_confirmation(order_hash):
    order = ds.get(ds.key("cendr-order", int(order_hash)))
    order["items"] = {x.split(":")[0]:int(x.split(":")[1]) for x in order['items']}
    if order is None:
        abort(404)
    page_title = "Order Number: " + str(order['order-number'])
    return render_template('order_confirm.html', **locals())


