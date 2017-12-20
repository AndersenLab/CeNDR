import hashlib
import markdown
import pytz
from flask import Blueprint
from datetime import datetime
from requests import post
from base.application import app, cache, get_ds, add_to_order_ws, send_mail
from flask import render_template, url_for, Markup, request, redirect
from base.emails import donate_submission
from base.utils.data import load_yaml
from base.views.api.api_strain import get_isotypes

about_bp = Blueprint('about',
                     __name__,
                     template_folder='about')


@about_bp.context_processor
def utility_processor():
    def render_markdown(filename, directory="base/static/content/markdown/"):
        with open(directory + filename) as f:
            return Markup(markdown.markdown(f.read()))
    return dict(render_markdown=render_markdown)


@about_bp.route('/')
@cache.cached()
def about():
    # About us Page - directs to other pages.
    title = "About"

    strain_listing = get_isotypes(known_origin=True)
    return render_template('about/about.html', **locals())


@about_bp.route('/getting_started/')
@cache.cached()
def getting_started():
    # About us Page - directs to other pages.
    title = "Getting Started"
    strain_listing = get_isotypes(known_origin=True)
    return render_template('about/getting_started.html', **locals())


@about_bp.route('/committee/')
@cache.cached()
def committee():
    # Scientific Panel Page
    title = "Scientific Advisory Committee"
    committee_data = load_yaml("advisory-committee.yaml")
    return render_template('about/committee.html', **locals())


@about_bp.route('/staff/')
@cache.cached()
def staff():
    # Staff Page
    title = "Staff"
    staff_data = load_yaml("staff.yaml")
    return render_template('about/staff.html', **locals())


@about_bp.route('/donate/', methods=['GET', 'POST'])
def donate():
    # Process donation.
    if request.method == 'POST':
        captcha_passed = False
        if 'g-recaptcha-response' in request.form:
            resp = post('https://www.google.com/recaptcha/api/siteverify',
                        data={'secret': app.config['RECAPTCHA_SECRET_KEY'],
                              'response': request.form['g-recaptcha-response']})
            if resp.json()['success']:
                captcha_passed = True
            else:
                captcha_passed = False
                warning = "Failed to pass captcha"

        if request.form and captcha_passed:
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
            order["items"] = u"{k}:{v}".format(
                k="CeNDR strain and data support", v=donation_amount)
            order["total"] = donation_amount
            order["is_donation"] = True
            order["date"] = datetime.now(pytz.timezone(
                "America/Chicago")).date().isoformat()
            order["invoice_hash"] = hashlib.sha1(str(order)).hexdigest()[0:10]
            order["url"] = "https://elegansvariation.org/order/" + \
                order["invoice_hash"]
            send_mail({"from": "no-reply@elegansvariation.org",
                       "to": [order["email"]],
                       "cc": ['dec@u.northwestern.edu',
                              'robyn.tanny@northwestern.edu',
                              'erik.andersen@northwestern.edu',
                              'g-gilmore@northwestern.edu',
                              'irina.iacobut@northwestern.edu'],
                       "cc": ['dec@u.northwestern.edu'],
                       "subject": "CeNDR Order #" + str(order["order_number"]),
                       "text": donate_submission.format(invoice_hash=order["invoice_hash"],
                                                        donation_amount=donation_amount)})

            add_to_order_ws(order)
            return redirect(url_for("order_confirmation", invoice_hash=order["invoice_hash"]), code=302)

    title = "Donate"
    return render_template('donate.html', **locals())


@about_bp.route('/funding/')
@cache.cached()
def funding():
    title = "Funding"
    funding_set = load_yaml('funding.yaml')
    return render_template('funding.html', **locals())
