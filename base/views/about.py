"""

    This set of views are the 'about' pages of the CeNDR site
    and additional miscellaneous extra pages (e.g. getting started)


"""
import markdown
from flask import Blueprint
from base.application import app, cache
from base.utils.google_sheets import add_to_order_ws
from base.forms import donation_form
from flask import render_template, url_for, Markup, request, redirect, session

from base.views.api.api_strain import get_isotypes

from base.utils.email import send_email, DONATE_SUBMISSION_EMAIL
from base.utils.data_utils import load_yaml, chicago_date, hash_it
from base.utils.google_sheets import add_to_order_ws


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
    VARS = {"title": "Getting Started",
            "strain_listing": get_isotypes(known_origin=True)}
    return render_template('about/getting_started.html', **VARS)


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


@about_bp.route('/donate/', methods=['GET', 'POST'])
def donate():
    """
        Process donation
    """
    title = "Donate"
    form = donation_form(request.form)

    # Autofill email
    if session.get('user') and not form.email.data:
        form.email.data = session.get('user')['user_email']

    if form.validate_on_submit():
        # order_number is generated as a unique string
        order_obj = {"is_donation": True,
                 "date": chicago_date()}
        order_obj['items'] = u"{}:{}".format("CeNDR strain and data support", form.data.get('total'))
        order_obj.update(form.data)
        order_obj['invoice_hash'] = hash_it(order_obj, length=8)
        order_obj['url'] = f"https://elegansvariation.org/order/{order_obj['invoice_hash']}"
        send_email({"from": "no-reply@elegansvariation.org",
                    "to": [order_obj["email"]],
                    "cc": app.config.get("CC_EMAILS"),
                    "cc": ['dec@u.northwestern.edu'],
                    "subject": f"CeNDR Dontaion #{order_obj['invoice_hash']}",
                    "text": DONATE_SUBMISSION_EMAIL.format(invoice_hash=order_obj["invoice_hash"],
                                                    donation_amount=order_obj.get('total'))})

        add_to_order_ws(order_obj)
        return redirect(url_for("order.order_confirmation", invoice_hash=order_obj["invoice_hash"]), code=302)

    return render_template('about/donate.html', **locals())


@about_bp.route('/funding/')
@cache.cached()
def funding():
    title = "Funding"
    funding_set = load_yaml('funding.yaml')
    return render_template('funding.html', **locals())
