"""

    This set of views are the 'about' pages of the CeNDR site
    and additional miscellaneous extra pages (e.g. getting started)


"""
import hashlib
import markdown
import pytz
import uuid
from flask import Blueprint
from datetime import datetime
from requests import post
from base.application import app, cache, get_ds, add_to_order_ws, send_mail
from base.forms import donation_form
from flask import render_template, url_for, Markup, request, redirect
from base.emails import donate_submission
from base.utils.data_utils import load_yaml
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
    """
        About us Page - Gives an overview of CeNDR
    """
    title = "About"

    strain_listing = get_isotypes(known_origin=True)
    return render_template('about/about.html', **locals())


@about_bp.route('/getting_started/')
@cache.cached()
def getting_started():
    """
        Getting Started - provides information on how to get started
        with CeNDR
    """
    title = "Getting Started"
    strain_listing = get_isotypes(known_origin=True)
    return render_template('about/getting_started.html', **locals())


@about_bp.route('/committee/')
@cache.cached()
def committee():
    """
        Scientific Panel Page
    """
    title = "Scientific Advisory Committee"
    committee_data = load_yaml("advisory-committee.yaml")
    return render_template('about/committee.html', **locals())


@about_bp.route('/staff/')
@cache.cached()
def staff():
    """
        Staff Page
    """
    title = "Staff"
    staff_data = load_yaml("staff.yaml")
    return render_template('about/staff.html', **locals())


def hash_it(object, length):
    return hashlib.sha1(str(hash(frozenset(object))).encode('utf-8')).hexdigest()[0:length]

def chicago_date():
    return datetime.now(pytz.timezone("America/Chicago")).date().isoformat()

@about_bp.route('/donate/', methods=['GET', 'POST'])
def donate():
    """
        Process donation
    """
    form = donation_form(request.form)

    if form.validate_on_submit():
        ds = get_ds()
        # order_number is generated as a unique string
        order = {}
        order.update(request.form.to_dict())
        order['is_donation'] = True
        order["items"] = u"{k}:{v}".format(
            k="CeNDR strain and data support", v=order.get('total'))
        order["date"] = chicago_date()
        order["invoice_hash"] = hash_it(order, length=8)
        order["url"] = f"https://elegansvariation.org/order/{order['invoice_hash']}"
        #send_mail({"from": "no-reply@elegansvariation.org",
        #           "to": [order["email"]],
        #           "cc": ['dec@u.northwestern.edu',
        #                  'robyn.tanny@northwestern.edu',
        #                  'erik.andersen@northwestern.edu',
        #                  'g-gilmore@northwestern.edu',
        #                  'irina.iacobut@northwestern.edu'],
        #           "cc": ['dec@u.northwestern.edu'],
        #           "subject": "CeNDR Order #" + str(order["order_number"]),
        #           "text": donate_submission.format(invoice_hash=order["invoice_hash"],
        #                                            donation_amount=donation_amount)})

        add_to_order_ws(order)
        return redirect(url_for("strain.order_confirmation", invoice_hash=order["invoice_hash"]), code=302)

    title = "Donate"
    return render_template('donate.html', **locals())


@about_bp.route('/funding/')
@cache.cached()
def funding():
    title = "Funding"
    funding_set = load_yaml('funding.yaml')
    return render_template('funding.html', **locals())
