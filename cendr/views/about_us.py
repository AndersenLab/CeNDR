from cendr import app, json_serial, cache, get_ds, add_to_order_ws, send_mail
from flask import render_template, url_for, Markup, request, redirect
import markdown
import yaml
import json
from cendr.models import strain, report, mapping, trait
from cendr.emails import donate_submission
from collections import OrderedDict
from gcloud.datastore.entity import Entity
from datetime import datetime
from cendr.emails import donate_submission
import pytz
import hashlib


@app.context_processor
def utility_processor():
    def render_markdown(filename, directory="cendr/static/content/markdown/"):
        with open(directory + filename) as f:
            return Markup(markdown.markdown(f.read()))
    return dict(render_markdown=render_markdown)


@app.route('/about/')
@cache.cached()
def about():
	# About us Page - directs to other pages.
    title = "About"
    bcs = OrderedDict([("About", None)])
    strain_listing = list(strain.select().filter(strain.isotype.is_null() == False)
        .filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('about.html', **locals())


@app.route('/getting_started/')
@cache.cached()
def getting_started():
    # About us Page - directs to other pages.
    title = "Getting Started"
    bcs = OrderedDict([("About", url_for("about")), ("Getting Started", "")])
    strain_listing = list(strain.select().filter(strain.isotype.is_null() == False)
        .filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('getting_started.html', **locals())




@app.route('/about/committee/')
@cache.cached()
def committee():
	# Scientific Panel Page
    title = "Scientific Advisory Committee"
    bcs = OrderedDict([("About", url_for("about")), ("Panel", "")])
    committee_data = yaml.load(open("cendr/static/content/data/advisory-committee.yaml", 'r'))
    return render_template('committee.html', **locals())


@app.route('/about/staff/')
@cache.cached()
def staff():
	# Staff Page
    title = "Staff"
    bcs = OrderedDict([("About", url_for("about") ), ("Staff", "")])
    staff_data = yaml.load(open("cendr/static/content/data/staff.yaml", 'r'))
    return render_template('staff.html', **locals())



@app.route('/about/statistics/')
@cache.cached()
def statistics():
    title = "Site Statistics"
    bcs = OrderedDict([("About", url_for("about")), ("Statistics", None)])

    # Number of reports
    n_reports = report.select().count()
    n_traits = trait.select().count()
    n_significant_mappings = mapping.select().count()
    n_distinct_strains = strain.select(strain.strain).distinct().count()
    n_distinct_isotypes = strain.select(strain.isotype).filter(strain.isotype != None).distinct().count()

    # Collection dates
    collection_dates = list(strain.select().filter(
        strain.isotype != None, strain.isolation_date != None).order_by(strain.isolation_date).execute())

    return render_template('statistics.html', **locals())



@app.route('/about/donate/', methods=['GET','POST'])
def donate():
    # Process donation.
    if request.form:
        ds = get_ds()
        donation_amount = str(int(request.form['donation_amount']))
        o = ds.get(ds.key("cendr-order", "count"))
        o["order-number"] += 1
        ds.put(o)
        order = {}
        order["order_number"] = o["order-number"]
        order["email"] = request.form["email"]
        order["address"] = request.form["address"]
        order["name"] = request.form["name"]
        order["items"] = u"{k}:{v}".format(k = "CeNDR strain and data support", v = donation_amount)
        order["total"] = donation_amount
        order["is_donation"] = True
        order["date"] = datetime.now(pytz.timezone("America/Chicago")).date().isoformat()
        order["invoice_hash"] = hashlib.sha1(str(order)).hexdigest()[0:10]
        order["url"] = "http://elegansvariation.org/order/" + order["invoice_hash"]
        send_mail({"from":"no-reply@elegansvariation.org",
           "to": [order["email"]],
           "cc": ['dec@u.northwestern.edu',
                  'robyn.tanny@northwestern.edu',
                  'erik.andersen@northwestern.edu',
                  'g-gilmore@northwestern.edu',
                  'irina.iacobut@northwestern.edu'],
           "subject":"CeNDR Order #" + str(order["order_number"]),
           "text": donate_submission.format(invoice_hash=order["invoice_hash"],
                                         donation_amount=donation_amount)})

        add_to_order_ws(order)

        return redirect(url_for("order_confirmation", invoice_hash=order["invoice_hash"]), code=302)

    title = "Donate"
    bcs = OrderedDict([("About", url_for("about")), ("Donate", None)])
    return render_template('donate.html', **locals())
    

@app.route('/about/funding/')
@cache.cached()
def funding():
    title = "Funding"
    bcs = OrderedDict([("About", url_for("about") ), ("Funding", "")])
    staff_data = yaml.load(open("cendr/static/content/markdown/funding.md", 'r'))
    return render_template('funding.html', **locals())
