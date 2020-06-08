#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook
"""
import glob
import os
import arrow
import pandas as pd
import traceback
import uuid
import json
import re
import logzero
import sys
from logzero import logger
from utils.interval import process_interval
from utils.gcloud import trait_m, mapping_m, query_item, get_item
from subprocess import Popen, STDOUT, PIPE, check_output
from io import StringIO
import requests

# Create a data directory
if not os.path.exists('data'):
    os.makedirs('data')

logzero.logfile("data/out.log", maxBytes=1e6, backupCount=3)

def send_email(send_to_email, subject, content):
    api_key = get_item('credential', 'mailgun')['apiKey']
    email = requests.post(
        "https://api.mailgun.net/v3/mail.elegansvariation.org/messages",
        auth=("api", api_key),
        data={"from": "CeNDR Admin <admin@elegansvariation.org>",
              "to": [send_to_email, "dec@u.northwestern.edu"],
              "subject": subject,
              "text": content})
    return email


def unique_id():
    return uuid.uuid4().hex

def run_comm(comm):
    logger.info(comm)
    process = Popen(comm, stdout=PIPE, stderr=sys.stderr)
    with process.stdout as proc:
        for line in proc:
            logger.info(str(line, 'utf-8').strip())

    return process

def fetch_existing_mapping(report_slug, trait_slug):
    """
        Used to fetch existing mappings
        if a job is rerun
    """
    trait_filters = [('report_slug', '=', report_slug), ('trait_slug', '=', trait_slug)]
    logger.info(trait_filters)
    try:
        result = list(query_item('mapping',
                                 filters=trait_filters))[0]
        mapping = mapping_m(result.key.name)
        mapping.__dict__.update(dict(result))
        return mapping
    except IndexError:
        return None

# Fetch trait info using ID


# Define variables
report_name = os.environ['REPORT_NAME']
trait_name = os.environ['TRAIT_NAME']
logger.info(f"Fetching Task: {report_name} - {trait_name}")

trait_filters = [('report_name', '=', report_name), ('trait_name', '=', trait_name)]
trait_data = list(query_item('trait',
                             filters=trait_filters))[0]


trait = trait_m(trait_data.key.name)
trait.__dict__.update(dict(trait_data))
trait._trait_df = pd.read_csv(StringIO(trait.trait_data), sep="\t")

# Output information about the run
run_comm(['echo', '$ECS_CONTAINER_METADATA_FILE'])

try:
    # Fetch cegwas version
    CEGWAS_VERSION = check_output("Rscript --verbose -e 'library(cegwas); devtools::session_info()' | grep 'cegwas'", shell=True)
    logger.info(CEGWAS_VERSION)
    trait.CEGWAS_VERSION = re.split(" +", str(CEGWAS_VERSION, encoding='UTF-8').strip())[2:]
    print(check_output("Rscript -e 'devtools::session_info()'", shell=True).decode('utf-8'))
    # Fetch container information
    try:
        trait.task_info = json.loads(check_output("echo ${ECS_CONTAINER_METADATA_FILE}", shell=True))
    except json.JSONDecodeError:
        pass

    trait._trait_df.to_csv('df.tsv', sep='\t', index=False)
    # Update report start time
    trait.started_on = arrow.utcnow().datetime
    trait.status = "running"
    trait.save()

    comm = ['Rscript', '--verbose', 'pipeline.R']
    process = run_comm(comm)
    exitcode = process.wait()

    logger.info(f"R exited with code {exitcode}")
    if exitcode != 0:
        raise Exception("R error")

    # Process significant data
    if os.path.exists("data/peak_summary.tsv.gz"):
        trait.is_significant = True
        peak_summary = pd.read_csv("data/peak_summary.tsv.gz", sep='\t')

        # Generate and save the interval summary
        interval_sums = [process_interval(x) for x in list(peak_summary.interval.values)]
        pd.concat(interval_sums) \
          .sort_values(['interval', 'variants'], ascending=False) \
          .to_csv("data/interval_summary.tsv.gz", sep="\t", compression='gzip', index=False)

        # Upload intervals as mapping objects
        for i, row in peak_summary.iterrows():
            mapping = fetch_existing_mapping(trait.report_slug, row.trait)
            if mapping is None:
                mapping = mapping_m(unique_id())
            chrom, interval_start, interval_end = re.split("\-|:", row.interval)
            mapping.chrom = chrom
            mapping.pos = row.POS
            mapping.interval_start = int(interval_start)
            mapping.interval_end = int(interval_end)
            try:
                mapping.is_public = trait.is_public
            except AttributeError:
                mapping.is_public = False
            mapping.log10p = row.peak_log10p
            mapping.report_slug = trait.report_slug
            mapping.trait_slug = trait.trait_name
            mapping.variance_explained = row.variance_explained
            mapping.save()
    else:
        trait.is_significant = False

    # Join variant data

    # Upload datasets
    trait.upload_files(glob.glob("data/*"))
    trait.status = "complete"
    send_email(trait.user_email,
               f"Trait Mapping Complete: {trait.report_slug}/{trait.trait_name}",
               f"Mapping of your trait has completed.\n\nhttp://www.elegansvariation.org/report/{trait.secret_hash}/{trait.trait_name}")

except Exception as e:
    traceback.print_exc()
    trait.error_message = str(e)
    trait.error_traceback = traceback.format_exc()
    trait.status = "error"
    traceback = traceback.format_exc()
    trait.completed_on = arrow.utcnow().datetime
    # Upload datasets for interrogating issues.
    trait.upload_files(glob.glob("data/*"))
    send_email(trait.user_email,
               f"Error - Mapping: {trait.report_slug}/{trait.trait_name}",
               f"Unfortunately, it looks like one of the mappings resulted in an error.\n\nhttp://www.elegansvariation.org/report/{trait.secret_hash}/{trait.trait_name}\n\n{traceback}")
finally:
    # Even when error occurs, upload artifacts to help diagnose.
    trait.completed_on = arrow.utcnow().datetime
    logger.info(trait)
    trait.save()
