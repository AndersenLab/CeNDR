"""

    This set of views are the 'about' pages of the CeNDR site
    and additional miscellaneous extra pages (e.g. getting started)


"""
import datetime
from io import StringIO
import pandas as pd
import requests
from flask import Blueprint
from flask import render_template, url_for, request, redirect, session
from base.utils.query import get_mappings_summary, get_weekly_visits, get_unique_users
from base.config import config
from base.models import Strain
from base.forms import donation_form
from base.views.api.api_strain import get_isotypes
from base.utils.google_sheets import add_to_order_ws
from base.utils.email import send_email, DONATE_SUBMISSION_EMAIL
from base.utils.data_utils import load_yaml, chicago_date, hash_it
from base.utils.plots import time_series_plot
from base.utils.jwt import jwt_required, get_current_user

about_bp = Blueprint('about',
                     __name__,
                     template_folder='about')


@about_bp.route('/')
def about():
    """
        About us Page - Gives an overview of CeNDR
    """
    title = "About"

    strain_listing = get_isotypes(known_origin=True)
    return render_template('about/about.html', **locals())


@about_bp.route('/getting_started/')
def getting_started():
    """
        Getting Started - provides information on how to get started
        with CeNDR
    """
    VARS = {"title": "Getting Started",
            "strain_listing": get_isotypes(known_origin=True)}
    return render_template('about/getting_started.html', **VARS)


@about_bp.route('/committee/')
def committee():
    """
        Scientific Panel Page
    """
    title = "Scientific Advisory Committee"
    committee_data = load_yaml("advisory-committee.yaml")
    return render_template('about/committee.html', **locals())

@about_bp.route('/collaborators/')
def collaborators():
    title = "Collaborators"
    collaborator_data = load_yaml("collaborators.yaml")
    return render_template('about/collaborators.html', **locals())


@about_bp.route('/staff/')
def staff():
    """
        Staff Page
    """
    title = "Staff"
    staff_data = load_yaml("staff.yaml")
    return render_template('about/staff.html', **locals())


@about_bp.route('/donate/', methods=['GET', 'POST'])
@jwt_required(optional=True)
def donate():
    """
        Process donation
    """
    title = "Donate"
    form = donation_form(request.form)

    # Autofill email
    user = get_current_user()
    if user and hasattr(user, 'email') and not form.email.data:
      form.email.data = user.email

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
                    "cc": config.get("CC_EMAILS"),
                    "subject": f"CeNDR Dontaion #{order_obj['invoice_hash']}",
                    "text": DONATE_SUBMISSION_EMAIL.format(invoice_hash=order_obj["invoice_hash"],
                                                           donation_amount=order_obj.get('total'))})

        add_to_order_ws(order_obj)
        return redirect(url_for("order.order_confirmation", invoice_hash=order_obj["invoice_hash"]), code=302)

    return render_template('about/donate.html', **locals())


@about_bp.route('/funding/')
def funding():
    title = "Funding"
    funding_set = load_yaml('funding.yaml')
    return render_template('about/funding.html', **locals())


@about_bp.route('/statistics')
def statistics():
    title = "Statistics"

    #
    # Strain collections plot
    #

    df = Strain.cum_sum_strain_isotype()
    strain_collection_plot = time_series_plot(df,
                                              x_title='Year',
                                              y_title='Count',
                                              range=[datetime.datetime(1995, 10, 17),
                                                     datetime.datetime.today()]
                                              )
    n_strains = max(df.strain)
    n_isotypes = max(df.isotype)

    #
    # Reports plot
    #
    df = get_mappings_summary()
    report_summary_plot = time_series_plot(df,
                                           x_title='Date',
                                           y_title='Count',
                                           range=[datetime.datetime(2016, 3, 1),
                                                  datetime.datetime.today()],
                                           colors=['rgb(149, 150, 255)', 'rgb(81, 151, 35)']
                                           )

    n_reports = int(max(df.reports))
    n_traits = int(max(df.traits))

    #
    # Weekly visits plot
    #
    df = get_weekly_visits()
    weekly_visits_plot = time_series_plot(df,
                                          x_title='Date',
                                          y_title='Count',
                                          range=[datetime.datetime(2016, 3, 1),
                                               datetime.datetime.today()],
                                          colors=['rgb(255, 204, 102)'])


    #
    # Unique users
    #
    n_users = get_unique_users()

    VARS = {'title': title,
            'strain_collection_plot': strain_collection_plot,
            'report_summary_plot': report_summary_plot,
            'weekly_visits_plot': weekly_visits_plot,
            'n_strains': n_strains,
            'n_isotypes': n_isotypes,
            'n_users': n_users,
            'n_reports': n_reports,
            'n_traits': n_traits}

    return render_template('about/statistics.html', **VARS)


@about_bp.route('/publications')
def publications():
    """
        List of publications that have referenced CeNDR
    """
    title = "Publications"
    csv_prefix = config['GOOGLE_SHEET_PREFIX']
    sheet_id = config['CENDR_PUBLICATIONS_STRAIN_SHEET']
    csv_export_suffix = 'export?format=csv&id={}&gid=0'.format(sheet_id)
    url = '{}/{}/{}'.format(csv_prefix, sheet_id, csv_export_suffix)
    req = requests.get(url)
    df = pd.read_csv(StringIO(req.content.decode("UTF-8")))
    df['pmid'] = df['pmid'].astype(int)
    df = df.sort_values(by='pmid', ascending=False)
    df = df.apply(lambda x: f"""<strong><a href="{x.url}">{x.title.strip(".")}</a>
                                </strong><br />
                                {x.authors}<br />
                                ( {x.pub_date} ) <i>{x.journal}</i>""", axis = 1)
    df = list(df.values)[:-1]
    return render_template('about/publications.html', **locals())
