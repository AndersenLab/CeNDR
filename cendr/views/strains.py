from cendr import app
from cendr import json_serial
from flask import render_template, request
from cendr.models import strain
from collections import OrderedDict
import json
import yaml
import stripe

stripe_keys = {
    'secret_key': "sk_test_1fmlHofOFzwqoxkPoP3E4RQ9",
    'publishable_key': "pk_test_fM3QofdBu9WCRvCkFIx8wgPl"
}

stripe.api_key = "sk_test_1fmlHofOFzwqoxkPoP3E4RQ9"

#
# Global Strain Map
#

@app.route('/strain/global-strain-map/')
def map_page():
    title = "Global Strain Map"
    bcs = OrderedDict([("strain", "/strain/"), ("global-strain-map", None)])
    strain_list_dicts = []
    strain_listing = list(strain.select().filter(strain.isotype.is_null() == False).filter(
        strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('map.html', **locals())


#
# Isotype View
#

@app.route('/strain/<isotype_name>/')
def isotype_page(isotype_name):
    page_type = "isotype"
    obj = isotype_name
    rec = list(strain.filter(strain.isotype == isotype_name).order_by(strain.latitude).dicts().execute())
    ref_strain = [x for x in rec if x["strain"] == isotype_name][0]
    strain_json_output = json.dumps([x for x in rec if x["latitude"] != None],  default=json_serial)
    return render_template('strain.html', **locals())


#
# Strain Catalog
#

@app.route('/strain/')
def strain_listing_page():
    bcs = OrderedDict([("strain", None)])
    title = "Strain Catalog"
    strain_listing = strain.select().filter(strain.isotype != None).order_by(strain.isotype).execute()
    return render_template('strain_catalog.html', **locals())

#
# Strain Submission
#

@app.route('/strain/submit/')
def strain_submission_page():
    bcs = OrderedDict([("strain", "submission")])
    title = "Strain Submission"
    return render_template('strain_submission.html', **locals())


#
# Protocols
#

@app.route("/strain/protocols/")
def protocols():
    title = "Protocols"
    bcs = OrderedDict([("strain", "/strain/"), ("protocols", "")])
    protocols = yaml.load(open("cendr/static/content/data/protocols.yaml", 'r'))
    return render_template('protocols.html', **locals())



#
# Strain Ordering Pages
# 


@app.route('/order/', methods=['POST'])
def order_page():
    bcs = OrderedDict([("strain", "/strain/"), ("order", "")])
    title = "Order"
    key = stripe_keys["publishable_key"]
    if 'stripeToken' in request.form:
        total = 500

        customer = stripe.Customer.create(
            email=request.form['stripeEmail'],
            card=request.form['stripeToken']
        )

        charge = stripe.Charge.create(
            customer=customer.id,
            amount=total,
            currency='usd',
            description='Flask Charge'
        )
        order_formatted = {k: autoconvert(v) for k, v in request.form.items()}
        order_formatted["price"] = total
        order_id = order.create(**order_formatted).save()
        return redirect(url_for("order_confirmation", order_id=request.form["stripeToken"][20:]), code=302)
    else:
        ordered = request.form.getlist('strain')
        # Calculate total
        ind_strains = len(ordered) * 1500
        total = ind_strains
        strain_listing = strain.select().where(strain.isotype << ordered).order_by(strain.isotype).execute()
        return render_template('order.html', **locals())


@app.route("/order/<order_id>/")
def order_confirmation(order_id):
    title = "Order: " + order_id
    query = "%" + order_id
    record = order.get(order.stripeToken ** query)
    return render_template('order_confirm.html', **locals())
