#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
import arrow
from utils.gcloud import report_m
from subprocess import Popen, STDOUT, PIPE


def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


create_dir("figures")
create_dir("tables")

# Define variables
report_name = os.environ['REPORT_NAME']
trait_name = os.environ['TRAIT_NAME']
print(f"Fetching Task: {report_name} - {trait_name}")
report = report_m(os.environ['REPORT_NAME'])
trait = report.fetch_traits(trait_name=trait_name, latest=True)


try:
    report._trait_df[['STRAIN', trait_name]].to_csv('df.tsv', sep='\t', index=False)
    # Update report start time
    trait.started_on = arrow.utcnow().datetime
    trait.run_status = "Running"
    trait.save()

    comm = ['Rscript', 'pipeline.R']
    process = Popen(comm, stdout=PIPE, stderr=STDOUT)
    with process.stdout as proc:
        for line in proc:
            print(str(line, 'utf-8').strip())
    exitcode = process.wait()
    print(f"R exited with code {exitcode}")
except Exception as e:
    trait.error_message = e
    trait.run_status = "Error"
else:
    trait.run_status = "Complete"
finally:
    trait.completed_on = arrow.utcnow().datetime
    trait.save()
