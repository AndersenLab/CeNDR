import os
import csv
import logging
from flask import render_template, request, send_from_directory, url_for, request,jsonify
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
import sys
from peewee import *
from playhouse import *
from slugify import slugify
import hashlib
import IPython
from models import *


app = Flask(__name__, static_url_path='/static')

@app.route('/')
def main():
    title = "Cegwas"
    return render_template('home.html', **locals())


@app.route('/map/')
def map_page():
    title = "Map"
    strain_list_dicts = []
    strain_listing = list(strain.select().filter(strain.isotype.is_null() == False).filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing])
    return render_template('map.html', **locals())


@app.route('/gwa/')
def gwa():
    title = "Run Association"
    strain_list = json.dumps([x.strain for x in strain.select(strain.strain).filter(strain.isotype.is_null() == False).execute()])
    return render_template('gwa.html', **locals())


def valid_url(url, encrypt):
    url_out = slugify(url)
    if encrypt:
        url_out = str(hashlib.sha224(url_out).hexdigest()[0:20])
    else:
        if report.filter(report.report_slug == url_out).count() > 0:
            return {'error': "Report name reserved."}
    if len(url_out) > 40:
        return {'error': "Report name may not be > 40 characters."}
    else:
        return url_out


@app.route('/process_gwa/', methods=['POST'])
def process_gwa():
    release_dict = {"public":0, "embargo6":1,  "embargo12":2,  "private":3}
    title = "Run Association"
    req = request.get_json()


    # Add Validation
    req["report_slug"] = valid_url(req["report_name"], req["release"] != 'public')
    data = req["trait_data"]
    del req["trait_data"]
    req["release"] = release_dict[req["release"]]
    req["version"] = 0.1
    trait_names = data[0][1:]
    with db.atomic():
        report_rec = report(**req)
        report_rec.save()
        trait_data = []
        for row in data[1:]:
            if row[0] is not None and row[0] != "":
                strain_name = strain.get(strain.strain == row[0])
                for k, v in zip(trait_names, row[1:]):
                    if v != None:
                        trait_data.append({"report": report_rec.id,
                                           "strain":strain_name.id,
                                           "name": k,
                                           "value": autoconvert(v)})
        print trait_data
        trait.insert_many(trait_data).execute()
    return 'success'


@app.route('/validate_url/', methods=['POST'])
def validate_url():
    """
        Generates URLs from report names and validates them.
    """
    req = request.get_json()
    # [ ] - Add Code to check against database that report (slug) is not already taken.
    url_out = valid_url(req["report_name"], req["release"] != 'public')
    if 'error' in url_out:
        return json.dumps({'error': url_out["error"]})
    else:
        return json.dumps({'report_name': url_out})


@app.route("/report/<name>/")
def report_view(name):
    title = name
    return name


@app.route('/strain/')
def strain_listing_page():
    title = "Wild Isolates"
    strain_listing = strain.select().filter(strain.isotype != None).order_by(strain.isotype).execute()
    return render_template('strain_listing.html', **locals())

@app.route('/strain/order', methods=['POST'])
def order_page():
    title = "Order"
    if 'strip_token' in request.form:
        amount = 500

        customer = stripe.Customer.create(
            email=request.form['stripeEmail'],
            card=request.form['stripeToken']
        )

        charge = stripe.Charge.create(
            customer=customer.id,
            amount=1500,
            currency='usd',
            description='Flask Charge'
        )
    else:
        ordered = request.form.getlist('strain')
        # Calculate total
        ind_strains = len(ordered)*1500
        total = ind_strains
        strain_listing = strain.select().where(strain.isotype << ordered).order_by(strain.isotype).execute()
    return render_template('order.html',**locals())



# [X] - change URL schema to be "/isotype/strain/"; Use url-for!
# [X] - Add breadcrumbs to strain page.
# [ ] - Add 'sister strains (shared isotypes)' to strain page.
# [ ] - Highlight isotype using ?=isotype get param

@app.route('/strain/<isotype_name>/')
def isotype_page(isotype_name):
    title = isotype_name + " | isotype"
    page_type = "isotype"
    obj = isotype_name
    rec = list(strain.filter(strain.isotype == isotype_name).order_by(strain.latitude).dicts().execute())
    ref_strain = [x for x in rec if x["strain"] == isotype_name][0]
    strain_json_output = json.dumps([x for x in rec if x["latitude"] != None])
    return render_template('strain.html', **locals())

@app.route('/strain/<isotype_name>/<strain_name>/')
def strain_page(isotype_name, strain_name):
    title = strain_name + " | strain"
    page_type = "strain"
    obj = strain_name
    rec = list(strain.filter(strain.strain == strain_name).dicts().execute())
    strain_json_output = json.dumps([x for x in rec if x["latitude"] != None])
    return render_template('strain.html', **locals())



if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug=True
    app.config['SECRET_KEY'] = '<123>'
    toolbar = DebugToolbarExtension(app)
    app.run(host='0.0.0.0', port=port)

