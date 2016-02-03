import os
import csv
import logging
from flask import render_template, request, send_from_directory, url_for, request, jsonify, redirect, Markup
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
import sys
from peewee import *
from playhouse import *
from slugify import slugify
import hashlib
import IPython
from collections import OrderedDict
from models import *
import stripe
import itertools
import mistune
from datetime import date


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, date):
        serial = obj.isoformat()
        return serial
    raise TypeError ("Type not serializable")


stripe_keys = {
    'secret_key': "sk_test_1fmlHofOFzwqoxkPoP3E4RQ9",
    'publishable_key': "pk_test_fM3QofdBu9WCRvCkFIx8wgPl"
}

stripe.api_key = "sk_test_1fmlHofOFzwqoxkPoP3E4RQ9"


app = Flask(__name__, static_url_path='/static')

@app.context_processor
def utility_processor():
    def render_markdown(filename, directory = "markdown/"):
        with open(directory + filename) as f:
            markdown = mistune.Markdown()
            return Markup(markdown(f.read()))
    return dict(render_markdown=render_markdown)


@app.route('/')
def main():
    title = "Cegwas"
    files = os.listdir("news/")
    files.reverse()
    return render_template('home.html', **locals())


@app.route('/map/')
def map_page():
    title = "Map"
    bcs = OrderedDict([("strain", "/strain/"), ("map", None)])
    strain_list_dicts = []
    strain_listing = list(strain.select().filter(strain.isotype.is_null() == False).filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('map.html', **locals())

@app.route('/data/')
def data_page():
    bcs = OrderedDict([("data", None)])
    title = "Data"
    strain_listing = strain.select().filter(strain.isotype != None).order_by(strain.isotype).execute()  
    return render_template('data.html', **locals())


@app.route('/gwa/')
def gwa():
    title = "Perform Mapping"
    bcs = OrderedDict([("Genetic Mapping", None), ("Perform Mapping", None)])

    # Generate list of allowable strains
    query = strain.select(strain.strain, 
            strain.isotype, 
            strain.previous_names).filter(strain.isotype.is_null() == False).execute()
    qresults = list(itertools.chain(*[[x.strain, x.isotype, x.previous_names] for x in query]))
    qresults = set([x for x in qresults if x != None])
    qresults = list(itertools.chain(*[x.split("|") for x in qresults]))

    strain_list = json.dumps(qresults)
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


@app.route('/about/')
def about():
    title = "About"
    bcs = OrderedDict([("about", "/about/")])
    return render_template('about.html', **locals())

@app.route('/about/staff/')
def staff():
    title = "Staff"
    bcs = OrderedDict([("about", "/about/"), ("staff", "")])
    return render_template('staff.html', **locals())

@app.route('/about/panel/')
def panel():
    title = "Scientific Advisory Panel"
    bcs = OrderedDict([("about", "/about/"), ("panel", "")])
    return render_template('panel.html', **locals())

@app.route('/about/statistics/')
def statistics():
    title = "Site Statistics"
    bcs = OrderedDict([("about", "/about/"), ("statistics", None)])

    # Collection dates
    collection_dates = list(strain.select().filter(strain.isotype != None, strain.isolation_date != None).order_by(strain.isolation_date).execute())

    return render_template('statistics.html', **locals())


@app.route('/strain/')
def strain_listing_page():
    bcs = OrderedDict([("strain", None)])
    title = "Strain Catalog"
    strain_listing = strain.select().filter(strain.isotype != None).order_by(strain.isotype).execute()  
    return render_template('strain_listing.html', **locals())

@app.route('/order/', methods=['POST'])
def order_page():
    bcs = OrderedDict([("strain","/strain/"), ("order","")])
    title = "Order"
    key = stripe_keys["publishable_key"]
    print request.form
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
        order_formatted = {k:autoconvert(v) for k,v in request.form.items()}
        order_formatted["price"] = total
        order_id = order.create(**order_formatted).save()
        return redirect(url_for("order_confirmation", order_id = request.form["stripeToken"][20:]), code=302)
    else:
        ordered = request.form.getlist('strain')
        print ordered
        # Calculate total
        ind_strains = len(ordered)*1500
        total = ind_strains
        strain_listing = strain.select().where(strain.isotype << ordered).order_by(strain.isotype).execute()
        return render_template('order.html',**locals())

@app.route("/order/<order_id>/")
def order_confirmation(order_id):
    title = "Order: " + order_id
    query = "%" + order_id
    record = order.get(order.stripeToken ** query)
    print record
    return render_template('order_confirm.html',**locals())

@app.route('/strain/<isotype_name>/')
def isotype_page(isotype_name):
    page_type = "isotype"
    obj = isotype_name
    rec = list(strain.filter(strain.isotype == isotype_name).order_by(strain.latitude).dicts().execute())
    ref_strain = [x for x in rec if x["reference_strain"] == isotype_name][0]
    strain_json_output = json.dumps([x for x in rec if x["latitude"] != None],  default=json_serial)
    return render_template('strain.html', **locals())


@app.route("/strain/protocols/")
def protocols():
    title = "Protocols"
    bcs = OrderedDict([("strain","/strain/"), ("protocols","")])
    return render_template('protocols.html', **locals())

@app.route("/news/")
def news():
    title = "Andersen Lab News"
    files = os.listdir("news/")
    files.reverse()
    bcs = OrderedDict([("News", "")])
    return render_template('news.html', **locals())

@app.route("/news/<filename>/")
def news_item(filename):
    title = filename[11:].strip(".md").replace("-"," ")
    return render_template('news_item.html', **locals())


@app.route('/outreach/')
def outreach():
    title = "Outreach"
    bcs = OrderedDict([("outreach", "/outreach/")])
    return render_template('outreach.html', **locals())



if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    #port = int(os.environ.get('PORT', 5000))
    app.debug=True
    app.config['SECRET_KEY'] = '<123>'
    toolbar = DebugToolbarExtension(app)
    app.run(debug=True, host='0.0.0.0')

