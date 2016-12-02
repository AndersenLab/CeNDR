#! /home/danielcook/.pyenv/shims/python
import os
import httplib2
import base64
import json
from apiclient import discovery
from oauth2client import client as oauth2client
from subprocess import check_output
from decimal import *
import time
from datetime import datetime
import pytz
import glob
import csv
import requests
from gcloud import logging
from StringIO import StringIO
import select
from subprocess import Popen, PIPE

def run_command(command, l):
    """
        Use to run commands
    """
    l.log_text(command, severity = "Info")
    p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
    e = p.wait()

    l.log_text(p.stdout.read(), severity = "Info")
    if e:
        # l.log_text(p.stderr.read(), severity = "Error")
        raise Exception(p.stderr.read())
    else:
        l.log_text(p.stderr.read(), severity = "Info")

def fetch_metadata(key):
    metadata_server = "http://metadata.google.internal/computeMetadata/v1/instance/attributes/"
    metadata_flavor = {'Metadata-Flavor' : 'Google'}
    return requests.get(metadata_server + key, headers = metadata_flavor).text


# Set up Logger
client = logging.Client()
# Set working directory
os.chdir("/home/danielcook/cegwas-worker/")

# Get instance information
gce_name = fetch_metadata('hostname')

# Fetch pipeline and models
pipeline_script = fetch_metadata('pipeline')
with open("pipeline.R", 'w') as f:
    f.write(pipeline_script)

# Fetch models
exec(fetch_metadata('models'))

def run_pipeline():
    report_slug = fetch_metadata('report_slug')
    report_name = fetch_metadata('report_name')
    trait_slug = fetch_metadata('trait_slug')
    trait_name = fetch_metadata('trait_name')
    release = fetch_metadata('release')
    l = client.logger(report_slug + "__" + trait_slug)
    l.log_text("Starting " + report_slug + "/" + trait_slug)
    l.log_text("gce_name:" + gce_name)
    # Get db trait and report.
    report_item = report.get(report_name = report_name)
    trait_item = trait.get(trait.report == report_item, trait.trait_slug == trait_slug)

    l.log_text("Starting Mapping: " + report_slug + "/" + trait_slug)
    # Refresh mysql connection
    db.close()
    db.connect()

    # Remove existing files if they exist
    l.log_text("Removing existing figures and tables.")
    [os.remove(x) for x in glob.glob("tables/*")]
    [os.remove(x) for x in glob.glob("figures/*")]

    # Run workflow
    args = {'report_slug': report_slug, 'trait_slug': trait_slug}
    args = json.dumps(args)
    comm = """Rscript pipeline.R '{args}'""".format(args = args)
    try:
        comm = """Rscript --verbose run.R '{args}'""".format(args = args)
        run_command(comm, l)

        # Refresh mysql connection
        l.log_text("Refreshing DB Connection")
        db.close()
        db.connect()

        # Upload results
        l.log_text("Uploading Files")
        upload1 = """gsutil -m cp -r figures gs://cendr/{report_slug}/{trait_slug}/""".format(**locals())
        check_output(upload1, shell = True)
        upload2 = """gsutil -m cp -r tables gs://cendr/{report_slug}/{trait_slug}/""".format(**locals())
        check_output(upload2, shell = True)

        # Insert records into database

        # Remove existing
        mapping.delete().where(mapping.report == report_item, mapping.trait == trait_item).execute()

        l.log_text("Inserting mapping_intervals.tsv")
        if os.path.isfile("tables/mapping_intervals.tsv"):
            with db.atomic():
                with open("tables/mapping_intervals.tsv", 'rb') as tsvin:
                    tsvin = csv.DictReader(tsvin, delimiter = "\t")
                    marker_set = []
                    for row in tsvin:
                        if row["startPOS"] != "NA" and row["marker"] not in marker_set:
                            marker_set.append(row["marker"])
                            mapping(chrom = row["CHROM"],
                                    pos = row["POS"],
                                    report = report_item,
                                    trait = trait_item,
                                    variance_explained = row["var.exp"],
                                    log10p = row["log10p"],
                                    BF = row["BF"],
                                    interval_start = row["startPOS"],
                                    interval_end = row["endPOS"],
                                    version = "0.1",
                                    reference = "WS245").save()

        # Refresh mysql connection
        l.log_text("Refreshing DB Connection")
        db.close()
        db.connect()

        # Insert Variant Correlation records into database.
        # Remove any existing
        mapping_correlation.delete().where(mapping_correlation.report == report_item, mapping_correlation.trait == trait_item).execute()

        l.log_text("Inserting mapping_intervals_db.tsv")
        if os.path.isfile("tables/interval_variants_db.tsv"):
            with db.atomic():
                with open("tables/interval_variants_db.tsv") as tsvin:
                    tsvin = csv.DictReader(tsvin, delimiter = "\t")
                    for row in tsvin:
                        mapping_correlation(report = report_item,
                                            trait = trait_item,
                                            CHROM = row["CHROM"],
                                            POS = row["POS"],
                                            gene_id = row["gene_id"],
                                            alt_allele = row["num_alt_allele"],
                                            num_strain = row["num_strains"],
                                            correlation = row["corrected_spearman_cor"]).save()

        # Update status of report submission
        trait.update(submission_complete=datetime.now(pytz.timezone("America/Chicago")), status="complete").where(trait.report == report_item, trait.trait_slug == trait_slug).execute()
        l.log_text("Finished " + report_slug + "/" + trait_slug, severity = "Info")
    except Exception as e:
        l.log_text(str(e), severity = "Error")
        trait.update(submission_complete=datetime.now(pytz.timezone("America/Chicago")), status="error").where(trait.report == report_item, trait.trait_slug == trait_slug).execute()


run_pipeline()

