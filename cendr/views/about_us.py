from cendr import app, json_serial, cache, ds
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



@app.route('/about/panel/')
@cache.cached()
def panel():
	# Scientific Panel Page
    title = "Scientific Advisory Panel"
    bcs = OrderedDict([("About", url_for("about")), ("Panel", "")])
    panel_data = yaml.load(open("cendr/static/content/data/advisory-panel.yaml", 'r'))
    return render_template('panel.html', **locals())


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
        donation_amount = int(request.form['donation_amount']) * 100
        o = ds.get(ds.key("cendr-order", "count"))
        o["order-number"] += 1
        order = Entity(ds.key('cendr-order'))
        items = {"CeNDR strain and data support": donation_amount}
        order["email"] = request.form["email"]
        order["items"] = [u"{k}:{v}".format(k=k, v=v) for k,v in items.items()]
        order["total"] = donation_amount
        order["donation"] = True
        order["submitted"] = datetime.now(pytz.timezone("America/Chicago"))
        order["order-number"] = o['order-number']
        with ds.transaction():
            ds.put(o)
            ds.put(order)
        order_hash = order.key.id
        from google.appengine.api import mail
        mail.send_mail(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
           to=order["email"],
           cc=['dec@u.northwestern.edu', 'robyn.tanny@northwestern.edu', 'erik.andersen@northwestern.edu'],
           subject="CeNDR Order #" + str(order["order-number"]),
           body=donate_submission.format(order_hash=order_hash))
        return redirect(url_for("order_confirmation", order_hash=order_hash), code=302)
    

    from google.appengine.api import mail
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
