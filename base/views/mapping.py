import hashlib
import decimal
import os
import time
import arrow

from base.utils.email import send_email, MAPPING_SUBMISSION_EMAIL

from base.application import autoconvert
from base.task.map_submission import launch_mapping
from base.models2 import report_m, trait_m
from base.models import db, report, strain, trait, trait_value, mapping
from datetime import date, datetime
import pytz
from dateutil.relativedelta import relativedelta
from peewee import JOIN
from flask import render_template, request, redirect, url_for, abort
from collections import OrderedDict
from slugify import slugify
import simplejson as json
from gcloud import storage
from collections import Counter
import requests
from base.forms import mapping_submission_form
from logzero import logger
from flask import session, flash, Blueprint, g
from base.utils.data_utils import unique_id
from base.constants import (REPORT_VERSION,
                            DATASET_RELEASE,
                            CENDR_VERSION,
                            WORMBASE_VERSION)

from base.utils.gcloud import query_item

from base.utils.plots import pxg_plot, plotly_distplot


mapping_bp = Blueprint('mapping',
                       __name__,
                       template_folder='mapping')


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, date):
            return str(o)
        return super(CustomEncoder, self).default(o)



@mapping_bp.route('/perform-mapping/', methods=['GET', 'POST'])
def mapping():
    """
        This is the mapping submission page.
    """
    form = mapping_submission_form(request.form)

    VARS = {'title': 'Perform Mapping',
            'form': form}

    user = session.get('user')
    logger.info(type(form.is_public.data))
    if form.validate_on_submit() and user:
        form.data.pop("csrf_token")
        report_slug = slugify(form.report_name.data)
        trait_list = list(form.trait_data.processed_data.columns[2:])
        strain_list = form.trait_data.strain_list
        report = report_m(report_slug)
        is_public = form.is_public.data
        trait_data = form.trait_data.processed_data.to_csv(index=False, sep="\t", na_rep="NA")
        report_name = form.report_name.data
        report_data = {'report_slug': slugify(form.report_name.data),
                       'report_name': report_name,
                       'description': form.description.data,
                       'trait_data': trait_data,
                       'created_on': arrow.utcnow().datetime,
                       'username': user['username'],
                       'user_id': user['user_id'],
                       'user_email': user['user_email'],
                       'is_public': is_public,
                       'trait_list': trait_list,
                       'strain_list': strain_list}
        if is_public is False:
            report_data['secret_hash'] = unique_id()[0:8]
        report_data = {k: v for k, v in report_data.items() if v}
        report.__dict__.update(report_data)

        # Begin a transaction so nothing is saved unless the tasks start
        # running.
        transaction = g.ds.transaction()
        transaction.begin()

        # Now generate and run trait tasks
        for trait_name in report.trait_list:
            trait = trait_m()
            trait.__dict__.update({
               'report_name': report_name,
               'report_slug': report_slug,
               'trait_name': trait_name,
               'created_on': arrow.utcnow().datetime,
               'run_status': 'Queued',
               'CENDR_VERSION': CENDR_VERSION,
               'REPORT_VERSION': REPORT_VERSION,
               'DATASET_RELEASE': DATASET_RELEASE,
               'WORMBASE_VERSION': WORMBASE_VERSION
            })
            trait.run_task()
        # Update the report to contain the set of the
        # latest task runs
        report.save()
        transaction.commit()

        flash("Successfully submitted mapping!", 'success')
        return redirect(url_for('mapping.report',
                                report_slug=report_slug,
                                trait_name=trait_list[0]))

    return render_template('mapping.html', **VARS)


@mapping_bp.route("/report/<report_slug>/")
@mapping_bp.route("/report/<report_slug>/<trait_name>")
@mapping_bp.route("/report/<report_slug>/<trait_name>/<rerun>")
def report(report_slug, trait_name=None, rerun=None):
    """
        This view will handle logic of handling legacy reports
        and v2 reports.

    """
    report = report_m(report_slug)
    if not report._exists and not report.is_public:
        # User is using private link - lookup using 'secret_hash'
        report = list(query_item('report', filters=[('secret_hash', '=', report_slug)]))
        if report:
            report = report_m(report[0].key.name)
            # Now fetch the task_run
        else:
            return abort(404)

    if not trait_name:
        # Redirect to the first trait
        return redirect(url_for('mapping.report',
                                report_slug=report_slug,
                                trait_name=report.trait_list[0]))

    # Fetch trait
    trait = report.fetch_traits(trait_name=trait_name)

    phenotype_plot = plotly_distplot(report._trait_df, trait_name)

    VARS = {
        'title': report.report_name,
        'subtitle': trait_name,
        'trait_name': trait_name,
        'report': report,
        'trait': trait,
        'strain_count': report.trait_strain_count(trait_name),
        'phenotype_plot': phenotype_plot,
    }


    # If the mapping is complete:
    if trait.is_complete:
        # Fetch peak marker data for generating the PxG plot
        
        # PxG Plot
        peak_marker_data = trait.get_gs_as_dataset("peak_markers.tsv")
        VARS['pxg_plot'] = pxg_plot(peak_marker_data, trait_name)
        
    # To handle report data, functions specific
    # to the version will be required.

    report_template = f"reports/{trait.REPORT_VERSION}.html"
    return render_template(report_template, **VARS)




@mapping_bp.route('/process_gwa/', methods=['POST'])
def process_gwa():
    release_dict = {"public": 0, "embargo12": 1,  "private": 2}
    req = request.get_json()

    # Add Validation
    rep_names = report_namecheck(req["report_name"])
    req["report_slug"] = rep_names["report_slug"]
    req["report_hash"] = rep_names["report_hash"]
    if 'error' in rep_names.keys():
        return ''
    data = req["trait_data"]
    del req["trait_data"]
    req["release"] = release_dict[req["release"]]
    req["version"] = 20170531
    trait_names = data[0][1:]
    strain_set = []
    trait_keep = []
    with db.atomic():
        report_rec = report(**req)
        report_rec.save()
        trait_data = []

        for row in data[1:]:
            if row[0] is not None and row[0] != "":
                q = row[0].strip().replace("(", "\(").replace(")", "\)")
                strain_name = resolve_strain_isotype(q)
                strain_set.append(strain_name)

        trait_set = data[0][1:]
        for n, t in enumerate(trait_set):
            trait_vals = [row[n + 1]
                          for row in data[1:] if row[n + 1]]
            if t and len(trait_vals) > 0:
                submit_time = datetime.now(pytz.timezone("America/Chicago"))
                trait_keep.append(t)
                trait_set[n] = trait.insert(report=report_rec,
                                            trait_name=t,
                                            trait_slug=slugify(t),
                                            status="queue",
                                            submission_date=submit_time).execute()
            else:
                trait_set[n] = None
        for col, t in enumerate(trait_set):
            for row, s in enumerate(strain_set):
                if t and s and is_number(data[1:][row][col + 1]):
                    val =  autoconvert(data[1:][row][col + 1])
                    trait_value(trait = t, strain = s, value = val).save()
                    trait_data.append({"trait": t,
                                       "strain": s,
                                       "value": val})
        #trait_value.insert_many(trait_data).execute()
    for t in trait_keep:
        req["trait_name"] = t
        req["trait_name"] = slugify(t)
        req["db_name"] = dbname
        req["submission_date"] = datetime.now(
            pytz.timezone("America/Chicago")).isoformat()
        # Submit job to task queue.
        launch_mapping(verify_request = False)
        req["success"] = True
        # Send user email
    if req["release"] > 0:
        report_slug = req["report_hash"]
    else:
        report_slug = req["report_slug"]
    send_email({"from":"no-reply@elegansvariation.org",
                   "to":[req["email"]],
                   "subject":"CeNDR Mapping Report - " + req["report_slug"],
                   "text": MAPPING_SUBMISSION_EMAIL.format(report_slug=report_slug)})

    return str(json.dumps(req))


@mapping_bp.route('/validate_url/', methods=['POST'])
def validate_url():
    """
        Generates URLs from report names and validates them.
    """
    req = request.get_json()
    return json.dumps(report_namecheck(req["report_name"]))


@mapping_bp.route('/Genetic-Mapping/public/', methods=['GET'])
def public_mapping():
    query = request.args.get("query")
    if query is not None:
        title = "Search: " + query
        subtitle = "results"
        q = "%" + query + "%"
        results = trait.select(report, trait, mapping).filter(trait.status == "complete", report.release == 0).join(mapping).join(report).dicts().filter((trait.trait_name % q) |
                                    (trait.trait_name % q) |
                                    (report.report_name % q) |
                                    (report.report_slug % q)).order_by(mapping.log10p.desc())
        search_results = list(results.dicts().execute())
        search = True
        return render_template('public_mapping.html', **locals())
    title = "Perform Mapping"
    results = trait.select(report.release, 
                                    report.report_name,
                                    report.report_slug,
                                    trait.trait_name,
                                    trait.trait_name,
                                    trait.status,
                                    trait.submission_complete,
                                    trait.submission_date,
                                    mapping) \
                           .filter(trait.status == "complete", 
                                   report.release == 0) \
                           .join(mapping, JOIN.LEFT_OUTER) \
                           .switch(trait) \
                           .join(report) \
                           .distinct() \
                           .dicts() \
                           .order_by(trait.submission_complete.desc()) \
                           .execute()

    date_set = dict(Counter([time.mktime((x["submission_date"]+relativedelta(hours = +6)).timetuple()) for x in results]))
    wdata = Counter([(x["submission_date"]+relativedelta(hours = +6)).date().isoformat() for x in results])
    waffle_date_set=[{"date":x, "count":y} for x,y in wdata.items()]

    #added in here waffle_date_set should be filtered by month instead of time stamp. Then could be used for the waffle plot
    #submission date is a datetime object
    #waffle_date_set=[]
    #sum=0
    #current_month=results[0]["submission_date"].month
    #for x in results:
    #    if x["submission_date"].month==current_month:
    #        sum++
    #    else:
    #        waffle_date_set.append(("month": current_month, "total": sum)) #appending a tuple
    #        sum=1
    #        current_month=x["submission_date"].month
    recent_results = list(results)[0:20]
    bcs = OrderedDict([("Public", None)])
    title = "Public Mappings"
    pub_mappings = list(mapping.select(mapping, report, trait).join(trait).join(report).filter(report.release == 0).dicts().execute())
    return render_template('public_mapping.html', **locals())



def trait_view(report_slug, trait_name="", rerun = None):

    report_data = list(report.select(report,
                                     trait,
                                     mapping.trait_id).join(trait).where(
                                    (
                                        (report.report_slug == report_slug) &
                                        (report.release == 0)
                                    ) |
                                    (
                                        (report.report_hash == report_slug) &
                                        (report.release > 0)
                                    )
                                ) \
                        .join(mapping, JOIN.LEFT_OUTER) \
                        .distinct() \
                        .dicts().execute())

    if not report_data:    
        return render_template('404.html'), 404


    if report_data[0]["release"] == 0:
        report_url_slug = report_data[0]["report_slug"]
    else:
        report_url_slug = report_data[0]["report_hash"]

     
    if not trait_name:
        return redirect(url_for("trait_view", report_slug=report_url_slug, trait_name=report_data[0]["trait_name"] ))
    else:
        try:
            trait_data = [x for x in report_data if x["trait_name"] == trait_name][0]
        except:
            # Redirect user to first trait if it can't be found.
            return redirect(url_for("trait_view", report_slug=report_url_slug, trait_name=report_data[0]["trait_name"] ))

    page_title = trait_data["report_name"] + " > " + trait_data["trait_name"]
    title = trait_data["report_name"]
    subtitle = trait_data["trait_name"]
    # Define report and trait slug 
    report_slug = trait_data["report_slug"] # don't remove
    trait_name = trait_data["trait_name"] # don't remove

    r = report.get(report_slug = report_slug)
    t = trait.get(report = r, trait_name = trait_name)

    # phenotype data
    #phenotype_data = list(trait_value.select(strain.strain, trait_value.value)
    #        .join(trait)
    #        .join(report)
    #        .switch(trait_value)
    #        .join(strain)
    #        .where(report.report_slug == r.report_slug)
    #        .where(trait.trait_name == t.trait_name)
    #        .dicts()
    #        .execute())
    phenotype_data = list(map(autoconvert, [x.split('\t')[2] for x in requests.get('https://storage.googleapis.com/cendr/{report_slug}/{trait_name}/tables/phenotype.tsv'.format(**locals())).text.splitlines()[1:]]))

    if rerun == "rerun":
        t.status = "queue"
        t.save()
        launch_mapping(verify_request = False)
        # Return user to current trait
        return redirect(url_for("trait_view", report_slug=report_url_slug, trait_name=trait_name))

    report_trait = "%s/%s" % (report_slug, trait_name)
    base_url = "https://storage.googleapis.com/cendr/" + report_trait

    # Fetch significant mappings
    mapping_results = list(mapping.select(mapping, report, trait)
                                  .join(trait)
                                  .join(report)
                                  .filter(
                                            (report.report_slug == report_slug), 
                                            (trait.trait_name == trait_name)
                                          ).dicts().execute())

    #######################
    # Variant Correlation #
    #######################
    var_corr = []
    for m in mapping_results:
        from base.views.api import correlation
        var_corr.append(correlation.get_correlated_genes(r, t, m["chrom"], m["interval_start"], m["interval_end"]))
    tbl_color = {"LOW": 'success', "MODERATE": 'warning', "HIGH": 'danger'}


    #######################
    # Fetch geo locations #
    #######################
    geo_gt = {}
    for m in mapping_results:
        try:
            result = GT.fetch_geo_gt(m["chrom"], m["pos"])
            geo_gt[m["chrom"] + ":" + str(m["pos"])] = result
        except:
            pass
    geo_gt = json.dumps(geo_gt)

    status = trait_data["status"]

    # List available datasets
    report_files = list(storage.Client(project='andersen-lab').get_bucket("cendr").list_blobs(
        prefix=report_trait + "/tables"))
    report_files = [os.path.split(x.name)[1] for x in report_files]


    # Fetch biotypes descriptions
    from base import biotypes

    return render_template('report.html', **locals())

@mapping_bp.route('/report_progress/', methods=['POST'])
def report_progress():
    """
        Generates URLs from report names and validates them.
    """
    req = request.get_json()
    current_status = list(trait.select(trait.status)
                          .join(report)
                          .filter(trait.trait_name == req["trait_name"], (report.report_slug == req["report_slug"]) | (report.report_hash == req["report_slug"]))
                          .dicts()
                          .execute())[0]["status"]
    return json.dumps(current_status)

