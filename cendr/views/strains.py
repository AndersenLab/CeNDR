from cendr import app, autoconvert, ds, db
from cendr import json_serial
from flask import render_template, request, url_for, redirect
from cendr.models import strain
from collections import OrderedDict
import json
import os
import yaml
import stripe
from google.appengine.api import mail
from cendr.emails import order_submission

if (os.getenv('SERVER_SOFTWARE') and
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    stripe_keys = ds.get(ds.key("credential", "stripe_live"))
else:
    stripe_keys = ds.get(ds.key("credential", "stripe_test"))

#
# Global Strain Map
#


@app.route('/strain/global-strain-map/')
def map_page():
    title = "Global Strain Map"
    bcs = OrderedDict([("strain", url_for("strain_listing_page")), ("global-strain-map", "")])
    strain_list_dicts = []
    strain_listing = list(strain.select().filter(strain.reference_strain == True)
        .filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('map.html', **locals())


#
# Isotype View
#

@app.route('/strain/<isotype_name>/')
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
def strain_listing_page():
    bcs = OrderedDict([("strain", None)])
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
    bcs = OrderedDict([("strain", url_for("strain_listing_page")), ("Strain Submission", "")])
    title = "Strain Submission"
    return render_template('strain_submission.html', **locals())


#
# Protocols
#

@app.route("/strain/protocols/")
def protocols():
    title = "Protocols"
    bcs = OrderedDict([("strain", url_for("strain_listing_page")), ("protocols", "")])
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
    bcs = OrderedDict([("strain", "/strain/"), ("order", "")])
    title = "Order"
    strain_listing = list(set(request.form.getlist('item')))
    items = request.form.getlist("item")
    # Retreive SKU's for prices
    items = calculate_total(items)
    total = sum(items.values())

    # Stripe can only process 25 items at once.
    if len(items) > 25:
        return redirect(url_for("strain_listing_page", warning = "A maximum of 25 items may be ordered (sets + strains)."))

    key = stripe_keys["public_key"]

    if 'stripeToken' in request.form:
        stripe.api_key = stripe_keys["secret_key"]
        try:
            customer = stripe.Customer.retrieve(request.form['stripeEmail'].lower())
        except:
            customer = stripe.Customer.create(
                id=request.form['stripeEmail'].lower(),
                email=request.form['stripeEmail'],
                card=request.form['stripeToken']
            )

        address = {
            "city": request.form["stripeShippingAddressCity"],
            "country": request.form["stripeShippingAddressCountry"],
            "line1": request.form["stripeShippingAddressLine1"],
            "postal_code": request.form["stripeShippingAddressZip"],
            "state": request.form["stripeShippingAddressState"]
        }

        if "stripeShippingAddressLine2" in request.form:
            address.update({"line2":request.form["stripeShippingAddressLine2"]})
        order = stripe.Order.create(
            currency = 'usd',
            items = [{"parent": m} for m in items.keys()],
            shipping = {
                        "name": request.form["stripeShippingName"],
                        "address": address,
                        "phone": None
                        },
            customer = customer.id,
            metadata = {"Shipping Service": request.form["shipping-service"],
                        "Shipping Account": request.form["shipping-account-number"]}
            )
        charge = stripe.Charge.create(
            customer=customer.id,
            order=order.id,
            receipt_email=customer.email,
            amount=order.amount,
            currency=order.currency,
            description='CeNDR Order',
            statement_descriptor='CeNDR Order'
        )
        # Send user email
        mail.send_mail(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
                to=customer.email,
                subject="CeNDR Order Submission " + order.id[3:],
                body=order_submission.format(order_slug=order.id[3:]))
        mail.send_mail_to_admins(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
                subject="CeNDR Order Submission " + order.id[3:],
                body=order_submission.format(order_slug=order.id[3:]))
        return redirect(url_for("order_confirmation", order_id=order.id), code=302)
    else:
        return render_template('order.html', **locals())


@app.route("/order/<order_id>/")
def order_confirmation(order_id):
    if order_id.startswith("or_"):
        order_id = order_id[3:]
    page_title = "Order: " + order_id
    stripe.api_key = stripe_keys["secret_key"]
    order = stripe.Order.retrieve("or_" + order_id)   
    print(order)     
    return render_template('order_confirm.html', **locals())





