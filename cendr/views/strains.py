from cendr import app, autoconvert, ds, db
from cendr import json_serial
from flask import render_template, request, url_for, redirect
from cendr.models import strain, order, order_strain
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

def calculate_total(strain_list):
    price_adjustment = 0
    strain_list = [x["isotype"] for x in strain.select(strain.isotype).where(strain.isotype << strain_list).distinct(strain.isotype).dicts().execute()]
    strain_sets = list(strain.select(strain.isotype, strain.set_1, strain.set_2, strain.set_3, strain.set_4, strain.set_divergent).distinct().dicts().execute())
    added_sets = []
    for i in range(1,5):
        set_test = [x["isotype"] for x in strain_sets if x["set_" + str(i)] is not None]
        if all([x in strain_list for x in set_test]):
            price_adjustment += 8000
            added_sets.append("set_" + str(i))
    # Divergent set
    set_divergent = [x["isotype"] for x in strain_sets if x["set_divergent"] is not None]
    if all([x in strain_list for x in set_divergent]):
            price_adjustment += 2000
            added_sets.append("divergent_set")
    return len(strain_list)*1000 - price_adjustment, price_adjustment, added_sets

@app.route('/order', methods=['GET','POST'])
def order_page():
    bcs = OrderedDict([("strain", "/strain/"), ("order", "")])
    title = "Order"
    strain_listing = list(set(request.form.getlist('isotype')))

    # Calculate total
    total, price_adjustment, added_sets = calculate_total(strain_listing)

    key = stripe_keys["public_key"]
    if 'stripeToken' in request.form:
        stripe.api_key = stripe_keys["secret_key"]
        customer = stripe.Customer.create(
            email=request.form['stripeEmail'],
            card=request.form['stripeToken']
        )

        charge = stripe.Charge.create(
            customer=customer.id,
            receipt_email=request.form['stripeEmail'],
            amount=total,
            currency='usd',
            description='Flask Charge',
            metadata={"strain_sets" : ", ".join(added_sets)}
        )

        order_formatted = {k: autoconvert(v) for k, v in request.form.items()}
        order_formatted["price"] = total
        order_formatted["charge"] = charge["id"]
        with db.atomic():
            order_created = order.create(**order_formatted)
            # NEED TO FILTER HERE FOR REFERENCE STRAINS
            strain_reference = list(strain.select(strain.strain).filter(strain.strain << strain_listing).filter(strain.reference_strain == True).dicts().execute())
            order_strain_insert = [{"order": order_created.id, "strain": strain.get(strain=x["strain"])} for x in strain_reference]
            order_strain.insert_many(order_strain_insert).execute()

        # Send user email
        mail.send_mail(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
                to=order_formatted["stripeEmail"],
                subject="CeNDR Order Submission " + order_formatted["stripeToken"][20:],
                body=order_submission.format(order_slug=order_formatted["stripeToken"][20:]))

        return redirect(url_for("order_confirmation", order_id=request.form["stripeToken"][20:]), code=302)
    else:
        n_strains = len(strain_listing)
        # [ ] ! Filter for strains that will be sent out here!
        strain_listing = strain.select().where(strain.isotype << strain_listing).order_by(strain.isotype).execute()
        return render_template('order.html', **locals())


@app.route("/order/<order_id>/")
def order_confirmation(order_id):
    page_title = "Order: " + order_id
    query = "%" + order_id
    record = order.get(order.stripeToken ** query)
    strain_listing = order.select(strain.strain, strain.isotype, order.stripeToken).join(order_strain).switch(order_strain).join(strain).filter(order.stripeToken ** query).dicts().execute()
    total, price_adjustment, added_sets = calculate_total([x["strain"] for x in strain_listing])
    return render_template('order_confirm.html', **locals())





