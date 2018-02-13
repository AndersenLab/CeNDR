#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import sys
import gzip
import glob
import os
import arrow
import pandas as pd
import traceback
import json
from logzero import logger
from utils.interval import process_interval
from utils.gcloud import report_m
from subprocess import Popen, STDOUT, PIPE

# Create a data directory
if not os.path.exists('data'):
    os.makedirs('data')

def run_comm(comm):
    process = Popen(comm, stdout=PIPE, stderr=STDOUT)
    with process.stdout as proc:
        for line in proc:
            print(str(line, 'utf-8').strip())
    return process

# Define variables
report_name = os.environ['REPORT_NAME']
trait_name = os.environ['TRAIT_NAME']
print(f"Fetching Task: {report_name} - {trait_name}")
report = report_m(os.environ['REPORT_NAME'])
trait = report.fetch_traits(trait_name=trait_name, latest=True)


try:
    report._trait_df[['STRAIN', 'ISOTYPE', trait_name]].to_csv('df.tsv', sep='\t', index=False)
    # Update report start time
    trait.started_on = arrow.utcnow().datetime
    trait.status = "Running"
    trait.save()

    comm = ['Rscript', 'pipeline.R']
    process = run_comm(comm)
    exitcode = process.wait()

    print(f"R exited with code {exitcode}")
    if exitcode != 0:
        raise Exception("R error")

    # Mark trait significant/insignificant
    trait.is_significant = True

    # Generate peak summaries
    peak_summary = pd.read_csv("data/peak_summary.tsv.gz", sep='\t')

    # Generate and save the interval summary
    interval_sums = [process_interval(x) for x in list(peak_summary.interval.values)]
    pd.concat(interval_sums) \
      .sort_values(['interval', 'variants'], ascending=False) \
      .to_csv("data/interval_summary.tsv.gz", sep="\t", compression='gzip', index=False)

    # Upload datasets
    trait.upload_files(glob.glob("data/*"))
    trait.status = "Complete"
except Exception as e:
    traceback.print_exc()
    trait.error_message = str(e)
    trait.error_traceback = traceback.format_exc()
    trait.status = "Error"
    trait.completed_on = arrow.utcnow().datetime
finally:
    trait.completed_on = arrow.utcnow().datetime
    logger.info(trait)
    trait.save()
