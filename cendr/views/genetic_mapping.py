from cendr import app
from cendr import ds
from cendr import autoconvert
from cendr.models import db, report, strain, trait, trait_value, mapping
from cendr.emails import mapping_submission
from google.appengine.api import mail
from datetime import date, datetime
import pytz
from peewee import fn
from dateutil.relativedelta import relativedelta
from peewee import JOIN

from flask import render_template, request, redirect, url_for
from collections import OrderedDict
import hashlib
import requests
import decimal
import itertools
from slugify import slugify
import hashlib
import simplejson as json
from iron_mq import IronMQ
from gcloud import storage
import os
import time
from collections import Counter
from pprint import pprint as pp

def get_queue():
    iron_credentials = ds.get(ds.key("credential", "iron"))
    return IronMQ(**dict(iron_credentials)).queue("cegwas-map")


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, date):
            return str(o)
        return super(CustomEncoder, self).default(o)

@app.route('/genetic-mapping/submit/')
def gwa():
    title = "Perform Mapping"
    bcs = OrderedDict([("genetic-mapping", None), ("perform-mapping", None)])

    # Generate list of allowable strains
    query = strain.select(strain.strain,
                          strain.isotype,
                          strain.previous_names).filter(strain.isotype.is_null() == False).execute()
    qresults = list(itertools.chain(
        *[[x.strain, x.isotype, x.previous_names] for x in query]))
    qresults = set([x for x in qresults if x != None])
    qresults = list(itertools.chain(*[x.split("|") for x in qresults]))

    embargo_release = (datetime.now(
            pytz.timezone("America/Chicago")) + relativedelta(years = 1)).strftime("%m/%d/%Y")

    strain_list = json.dumps(qresults)
    return render_template('gwa.html', **locals())


def valid_url(url, encrypt):
    url_out = slugify(url)
    if report.filter(report.report_slug == url_out).count() > 0:
        return {'error': "Report name reserved."}
    if encrypt:
        url_out = str(hashlib.sha224(url_out).hexdigest()[0:20])
    if len(url_out) > 40:
        return {'error': "Report name may not be > 40 characters."}
    else:
        return url_out


def report_namecheck(report_name):
    report_slug = slugify(report_name)
    report_hash = str(hashlib.sha224(report_slug).hexdigest()[0:20])
    if report.filter(report.report_slug == report_slug).count() > 0:
        return {'error': "Report name reserved."}
    if len(report_slug) > 40:
        return {'error': "Report name may not be > 40 characters."}
    else:
        return {"report_slug": report_slug, "report_hash": report_hash}

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


@app.route('/process_gwa/', methods=['POST'])
def process_gwa():
    release_dict = {"public": 0, "embargo12": 1,  "private": 2}
    title = "Run Association"
    req = request.get_json()

    queue = get_queue()

    # Add Validation
    rep_names = report_namecheck(req["report_name"])
    req["report_slug"] = rep_names["report_slug"]
    req["report_hash"] = rep_names["report_hash"]
    data = req["trait_data"]
    del req["trait_data"]
    req["release"] = release_dict[req["release"]]
    req["version"] = 1
    trait_names = data[0][1:]
    strain_set = []
    trait_keep = []
    with db.atomic():
        report_rec = report(**req)
        report_rec.save()
        trait_data = []

        for row in data[1:]:
            if row[0] is not None and row[0] != "":
                row[0] = row[0].strip().replace("(", "\(").replace(")", "\)")
                strain_name = strain.filter((strain.strain == row[0]) |
                                            (strain.isotype == row[0]) |
                                            (strain.previous_names.regexp('^(' + row[0] + ')\|')) |
                                            (strain.previous_names.regexp('\|(' + row[0] + ')$')) |
                                            (strain.previous_names.regexp('\|(' + row[0] + ')\|')) |
                                            (strain.previous_names == row[0]))
                # precedence of strain submission:
                strain_match = [x for x in strain_name if x.strain == row[0]]
                isotype_match = [x for x in strain_name if x.isotype == row[0]]
                if len(strain_match) > 0:
                    strain_set.append(list(strain_match)[0])
                elif len(isotype_match) > 0:
                    strain_set.append(list(isotype_match)[0])
                else:
                    strain_set.append(list(strain_match)[0])

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
                    trait_data.append({"trait": t,
                                       "strain": s,
                                       "value": autoconvert(data[1:][row][col + 1])})
        trait_value.insert_many(trait_data).execute()
    for t in trait_keep:
        req["trait_name"] = t
        req["trait_slug"] = slugify(t)
        req["submission_date"] = datetime.now(
            pytz.timezone("America/Chicago")).isoformat()
        # Submit job to iron worker
        resp = queue.post(str(json.dumps(req)))
        req["success"] = True
        # Send user email
    if req["release"] > 0:
        report_slug = req["report_hash"]
    else:
        report_slug = req["report_slug"]
    mail.send_mail(sender="CeNDR <andersen-lab@appspot.gserviceaccount.com>",
                   to=req["email"],
                   subject="CeNDR Mapping Report - " + req["report_slug"],
                   body=mapping_submission.format(report_slug=report_slug))

    return str(json.dumps(req))


@app.route('/validate_url/', methods=['POST'])
def validate_url():
    """
        Generates URLs from report names and validates them.
    """
    req = request.get_json()
    return json.dumps(report_namecheck(req["report_name"]))


@app.route('/Genetic-Mapping/public/', methods=['GET'])
def public_mapping():
    query = request.args.get("query")
    if query is not None:
        bcs = OrderedDict([("genetic-mapping", None), ("Public Mappings", url_for('public_mapping')), ("Search", None)])
        title = "Search: " + query
        subtitle = "results"
        q = "%" + query + "%"
        results = trait.select(report, trait, mapping).filter(trait.status == "complete", report.release == 0).join(mapping).join(report).dicts().filter((trait.trait_slug % q) |
                                    (trait.trait_name % q) |
                                    (report.report_name % q) |
                                    (report.report_slug % q)).order_by(mapping.log10p.desc())
        search_results = list(results.dicts().execute())
        search = True
        return render_template('public_mapping.html', **locals())
    title = "Perform Mapping"
    recent_results = trait.select(report.release, 
                                    report.report_name,
                                    report.report_slug,
                                    trait.trait_name,
                                    trait.trait_slug,
                                    trait.status,
                                    trait.submission_complete, mapping).filter(trait.status == "complete", report.release == 0).join(mapping, JOIN.LEFT_OUTER).switch(trait).join(report).distinct().dicts().order_by(trait.submission_complete.desc()).execute()

    dates = recent_results
    date_set = dict(Counter([time.mktime((x["submission_complete"]+relativedelta(hours = +6)).timetuple()) for x in dates]))
    # recent_results.reverse()
    bcs = OrderedDict([("genetic-mapping", None), ("public", None)])
    title = "Public Mappings"
    pub_mappings = list(mapping.select(mapping, report, trait).join(trait).join(report).filter(report.release == 0).dicts().execute())
    return render_template('public_mapping.html', **locals())


@app.route("/report/<report_slug>/")
@app.route("/report/<report_slug>/<trait_slug>")
@app.route("/report/<report_slug>/<trait_slug>/<rerun>")
def trait_view(report_slug, trait_slug="", rerun = None):
    report_data = list(trait.select(trait, report).join(report).where(((report.report_slug == report_slug) & (
        report.release == 0)) | (report.report_hash == report_slug)).dicts().execute())
    if trait_slug:
        try:
            trait_data = [x for x in report_data if x["trait_slug"] == trait_slug][0]
        except:
            # Trait report not found:
            return render_template('404.html'), 404
        title = trait_data["report_name"]
        subtitle = trait_data["trait_name"]
        if trait_data["release"] == 0:
            report_url_slug = trait_data["report_slug"]
        else:
            report_url_slug = trait_data["report_hash"]
        if rerun == "rerun":
            if trait_data["status"] == "error":
                queue = get_queue()
                print trait_data
                #trait_data["submission_date"] = datetime.now(
                #    pytz.timezone("America/Chicago")).isoformat()
                # Submit job to iron worker
                queue.post(str(json.dumps(trait_data, cls=CustomEncoder)))
            # Return user to current trait
            return redirect(url_for("trait_view", report_slug=trait_data["report_slug"], trait_slug=trait_data["trait_slug"]))

    else:
        # Redirect to first trait always.
        try:
            first_trait = list(report_data)[0]
            return redirect(url_for("trait_view", report_slug=report_slug, trait_slug=first_trait["trait_slug"]))
        except:
            return render_template('404.html'), 404

    # Redifine report slug as actual slug (instead of hash)
    report_slug = trait_data["report_slug"]
    base_url = "https://storage.googleapis.com/cendr/" + report_slug + "/" + trait_slug

    # Fetch significant mappings
    mapping_results = list(mapping.select(mapping, report, trait).join(trait).join(report).filter((report.report_slug == report_slug),(trait.trait_slug == trait_slug)).dicts().execute())
    status = list(trait.select(report, trait).join(report).filter((report.report_slug == report_slug),(trait.trait_slug == trait_slug)).dicts().execute())[0]

    # List available datasets
    report_files = list(storage.Client().get_bucket("cendr").list_blobs(
        prefix=report_slug + "/" + trait_slug + "/tables"))
    report_files = [os.path.split(x.name)[1] for x in report_files]

    report_url = base_url + "/report.html"
    report_html = requests.get(report_url).text.replace(
        'src="', 'src="' + base_url + "/")
    if not report_html.startswith("<?xml"):
        report_html = report_html[report_html.find(
            '<body>'):report_html.find("</body>")].replace("</body>", "").replace("<body>","").replace('<h1 class="title">cegwas results</h1>', "")
    else:
        report_html = ""
    return render_template('report.html', **locals())

@app.route('/report_progress/', methods=['POST'])
def report_progress():
    """
        Generates URLs from report names and validates them.
    """
    req = request.get_json()
    current_status = list(trait.select(trait.status)
                          .join(report)
                          .filter(trait.trait_slug == req["trait_slug"], (report.report_slug == req["report_slug"]) | (report.report_hash == req["report_slug"]))
                          .dicts()
                          .execute())[0]["status"]
    return json.dumps(current_status)


@app.route('/genetic-mapping/status/')
def status_page():
    # queue
    bcs = OrderedDict([("genetic-mapping", None), ("status", None)])
    title = "Status"
    queue = get_queue()
    ql = [json.loads(x["body"]) for x in queue.peek(max=100)["messages"]]
    qsize = queue.size()

    from googleapiclient import discovery
    from oauth2client.client import GoogleCredentials
    credentials = GoogleCredentials.get_application_default()
    compute = discovery.build('compute', 'v1', credentials=credentials)

    # Get instance list
    instances = compute.instances().list(project="andersen-lab", zone="us-central1-a",
                                         filter="status eq RUNNING").execute()
    if 'items' in instances:
        instances = [x["name"] for x in instances["items"]]
    else:
        instances = []
    workers = []
    for w in instances:
        query = ds.query(kind="Worker")
        query.add_filter('full_name', '=', w + ".c.andersen-lab.internal")
        worker_list = list(query.fetch())
        if len(worker_list) > 0:
            workers.append(worker_list[0])

    recently_complete = list(report.select(report, trait).filter(trait.submission_complete != None).join(trait).order_by(
        trait.submission_complete.desc()).limit(10).dicts().execute())

    return render_template('status.html', **locals())
