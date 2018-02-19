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
from base.models2 import user_m, trait_m, mapping_m
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

            
with app.app_context():
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
        trait.is_public = row['release'] in [0, 1]
        trait.secret_hash = row.get('secret_hash')
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
        trait.status = row['status']
        trait.trait_name = row['trait_slug']
        trait.trait_list = list(set(reports[reports.report_slug == trait.report_slug].trait_slug.values))
        trait.is_significant = len(mappings[(mappings.report_name == trait.report_name) & (mappings.trait_slug == trait.trait_name)]) > 0
        user = get_item('user', row['email'].lower())
        trait.user_email = user['user_email']
        trait.user_id = user['user_id']
        trait.save()


var_corr = pd.read_csv("base/report_conversion/var_corr.csv")

var_corr['interval'] = var_corr.apply(lambda row: f"{row.CHROM}:{row.interval_start}-{row.interval_end}", axis=1)

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

# Mapping intervals
intervals = pd.read_csv("base/report_conversion/mapping_intervals.csv")
with app.app_context():
    for row in reports.to_dict('records'):
        sliced = intervals[(intervals.report_slug == row['report_slug']) & (intervals.trait_slug == row['trait_slug'])]
        sliced = sliced[['chrom','pos','variance_explained', 'log10p', 'BF', 'interval_start', 'interval_end', 'report_slug', 'trait_slug']]
        sliced.to_csv('out.tsv.gz',sep='\t', compression='gzip')
        report_base = f"reports/v1/{row['report_slug']}/{row['trait_slug']}/tables/peak_summary.tsv.gz"
        print(report_base)
        cendr_bucket.blob(report_base).upload_from_filename('out.tsv.gz')






# Create datastore for mapping intervals
intervals = pd.read_csv("base/report_conversion/mapping_intervals.csv")
with app.app_context():
    for index, row in intervals.iterrows():
        if row.status == 'complete':
            vals = {'report_slug': row.report_slug,
                    'trait_slug': row.trait_slug,
                    'chrom': row.chrom,
                    'pos': row.pos,
                    'variance_explained': row.variance_explained,
                    'log10p': row.log10p,
                    'interval_start': row.interval_start,
                    'interval_end': row.interval_end,
                    'is_public': row.release in [0, 1]}
            mapping = mapping_m(unique_id())
            mapping.__dict__.update(vals)
            print(mapping.__dict__)
            mapping.save()



