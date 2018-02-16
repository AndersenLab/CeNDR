#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

This script is used to convert data from the SQL database to the new datastore database.

"""
import arrow
import sys
import os
os.chdir('../../')
sys.path.append(".")
os.environ['GAE_VERSION'] = 'development-1'
from base.application import app
import pandas as pd
from base.utils.gcloud import store_item, get_item, query_item
from base.utils.data_utils import unique_id
from base.models2 import user_m, report_m, trait_m
from slugify import slugify
from gcloud import storage


# Generate users
report = pd.read_csv("base/report_conversion/report_trait.csv")
user_emails = report.email.apply(lambda x: x.lower()).unique()


def fetch_all(query):
    records = []
    while True:
        data, more, key = query.next_page()
        records.extend(data)
        if more is False:
            break
    return records

user_set = query_item('user')

with app.app_context():
    for user_email in user_emails:
        user = user_m(user_email)
        if not user._exists:
            user.user_email = user_email.lower()
            user.user_info = {}
            user.email_confirmation_code = unique_id()
            user.user_id = unique_id()[0:8]
            user.username = slugify("{}_{}".format(user_email.split("@")[0], unique_id()[0:4]))
        user.last_login = arrow.utcnow().datetime
        user.save()



# Create reports
reports = pd.read_csv("base/report_conversion/report_trait.csv")
mappings = pd.read_csv("base/report_conversion/mapping_significant.csv")

report_set = query_item('report')
report_slugs = [x['report_slug'] for x in report_set]

with app.app_context():
    report_set = []
    for slug in reports['report_slug'].dropna().unique():
        '''
            Redundant but quick and easy...
        '''
        if slug not in report_slugs:
            row = reports[reports.report_slug == slug].iloc[0]
            report = report_m(row['report_slug'])
            report.report_name = row['report_name']
            report.trait_name = row['trait_name']
            report.report_slug = row['report_slug']
            report.is_public = row['release'] in [0, 1]
            report.secret_hash = row.get('secret_hash')
            report.status = row['status']
            report.trait_list = list(reports[reports.report_slug == row['report_slug']].trait_slug.values)
            #report.CENDR_VERSION = "<=1.1.4"
            #report.DATASET_RELEASE = row['version']
            #report.REPORT_VERSION = 'v1'
            report.created_on = arrow.get(row['submission_date']).datetime
            user = get_item('user', row['email'].lower())
            report.user_id = user['user_id']
            report.username = user['username']
            report.user_email = user['user_email']
            #if row['version'] == 20170408:
            #    report.WORMBASE_VERSION = 'WS245'
            #else:
            #    report.WORMBASE_VERSION = 'WS261'
            print(report.__dict__)
            report.save()
            

trait_set = query_item('trait')
report_traits = [x['report_trait'] for x in trait_set]

with app.app_context():
    for row in reports.to_dict('records'):
        '''
            Redundant but quick and easy...
        '''
        trait = trait_m("v1-report:" + row['trait_slug'])
        trait.CENDR_VERSION = "<=1.1.4"
        trait.REPORT_VERSION = 'v1'
        trait.DATASET_RELEASE = str(row.get('version'))
        if row['version'] == 20170408:
            trait.WORMBASE_VERSION = 'WS245'
        else:
            trait.WORMBASE_VERSION = 'WS261'
        try:
            trait.completed_on = arrow.get(row['submission_complete']).datetime
        except OSError:
            continue
        trait.created_on = arrow.get(row['submission_date']).datetime
        trait.report_name = str(row['report_name'])
        trait.report_slug = str(row['report_slug'])
        trait.report_trait = str(row['report_slug']) + ":" + str(row['trait_name'])
        print(trait.report_trait in report_traits)
        if trait.report_trait not in report_traits:
            trait.status = row['status']
            trait.trait_name = row['trait_slug']
            trait.is_significant = len(mappings[(mappings.report_name == trait.report_name) & (mappings.trait_slug == trait.trait_name)]) > 0
            user = get_item('user', row['email'].lower())
            trait.user_email = user['user_email']
            trait.save()

"""
var_corr = pd.read_csv("base/report_conversion/variant_correlation.csv")

# Upload variant correlation
with app.app_context():
    gs = storage.Client(project='andersen-lab')
    cendr_bucket = gs.get_bucket("elegansvariation.org")
    for row in reports.to_dict('records'):
        vc = var_corr[(var_corr.report_slug == row['report_slug']) & (var_corr.trait_slug == row['trait_slug'])]
        if len(vc) > 0:
            fname = "upload/variant_correlation.tsv.gz"
            vc.to_csv(fname, compression='gzip', sep='\t')
            report_base = f"reports/v1/{row['report_slug']}/{row['trait_slug']}/tables/variant_correlation.tsv.gz"
            print(report_base)
            cendr_bucket.blob(report_base).upload_from_filename(fname)
"""