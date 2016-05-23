from cendr import app, json_serial, cache
from flask import render_template, url_for, Markup, request
import markdown
import yaml
import json
import stripe
from cendr import get_stripe_keys
from cendr.models import strain, report, mapping, trait
from google.appengine.api import mail
from cendr.emails import donate_submission
from collections import OrderedDict

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
    bcs = OrderedDict([("about", None)])
    strain_listing = list(strain.select().filter(strain.isotype.is_null() == False)
        .filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('about.html', **locals())



@app.route('/about/panel/')
@cache.cached()
def panel():
	# Scientific Panel Page
    title = "Scientific Advisory Panel"
    bcs = OrderedDict([("about", url_for("about")), ("panel", "")])
    panel_data = yaml.load(open("cendr/static/content/data/advisory-panel.yaml", 'r'))
    return render_template('panel.html', **locals())


@app.route('/about/staff/')
@cache.cached()
def staff():
	# Staff Page
    title = "Staff"
    bcs = OrderedDict([("about", url_for("about") ), ("staff", "")])
    staff_data = yaml.load(open("cendr/static/content/data/staff.yaml", 'r'))
    return render_template('staff.html', **locals())



@app.route('/about/statistics/')
@cache.cached()
def statistics():
    title = "Site Statistics"
    bcs = OrderedDict([("about", url_for("about")), ("statistics", None)])

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



@app.route('/donate/', methods=['GET','POST'])
def donate():
    title = "Donate"
    bcs = OrderedDict([("donate", "")])
    print(request.form)
    stripe_keys = get_stripe_keys()
    key = stripe_keys["public_key"]
    # Process form if stripe token available.
    if 'stripeToken' in request.form:
        print(request.form)
        token = request.form['stripeToken']
        donation = int(request.form.get('amount')) * 100
        stripe.api_key = stripe_keys["secret_key"]
        try:
            customer = stripe.Customer.retrieve(request.form['stripeEmail'].lower())
        except:
            customer = stripe.Customer.create(
                id=request.form['stripeEmail'].lower(),
                email=request.form['stripeEmail'],
            )
        charge = stripe.Charge.create(
            receipt_email=customer.email,
            amount=donation,
            source=token,
            currency='usd',
            description='CeNDR Donation',
            statement_descriptor='CeNDR Donation'
        )
        # Send user email
        mail.send_mail(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
                to=customer.email,
                subject="CeNDR Donation",
                body=donate_submission.format(donation=donation))
        mail.send_mail_to_admins(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
                subject="Donation to CeNDR",
                body=donate_submission.format(donation=donation))
        return render_template('donate.html', **locals())

    else:
        return render_template('donate.html', **locals())

@app.route('/about/funding/')
@cache.cached()
def funding():
    title = "Funding"
    bcs = OrderedDict([("about", url_for("about") ), ("Funding", "")])
    staff_data = yaml.load(open("cendr/static/content/markdown/funding.md", 'r'))
    return render_template('funding.html', **locals())
