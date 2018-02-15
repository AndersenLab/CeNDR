#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

This script is used to convert data from the SQL database to the new datastore database.

"""
import arrow
import sys
import os
import arrow
os.chdir('../../')
sys.path.append(".")
os.environ['GAE_VERSION'] = 'development-1'
from base.application import app
import pandas as pd
from base.utils.gcloud import store_item, get_item
from base.utils.data_utils import unique_id
from base.models2 import user_m, report_m, trait_m
from slugify import slugify

"""
# Generate users
report = pd.read_csv("base/report_conversion/report_view.csv")
user_emails = report.email.apply(lambda x: x.lower()).unique()

with app.app_context():
    for user_email in user_emails:
        user = user_m(user_email)
        if not user._exists:
            user.user_email = user_email
            user.user_info = {}
            user.email_confirmation_code = unique_id()
            user.user_id = unique_id()[0:8]
            user.username = slugify("{}_{}".format(user_email.split("@")[0], unique_id()[0:4]))
        user.last_login = arrow.utcnow().datetime
        user.save()
"""


# Create reports
reports = pd.read_csv("base/report_conversion/report_trait.csv")
mappings = pd.read_csv("base/report_conversion/mapping_significant.csv")
"""
print(reports)
with app.app_context():
    for row in reports.to_dict('records'):
        '''
            Redundant but quick and easy...
        '''
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
        user = get_item('user', row['email'])
        report.user_id = user['user_id']
        report.username = user['username']
        report.user_email = user['user_email']
        #if row['version'] == 20170408:
        #    report.WORMBASE_VERSION = 'WS245'
        #else:
        #    report.WORMBASE_VERSION = 'WS261'
        report.save()
"""


print(reports)
with app.app_context():
    for row in reports.to_dict('records'):
        '''
            Redundant but quick and easy...
        '''
        print(row)
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
        trait.report_name = row['report_name']
        trait.report_slug = row['report_slug']
        trait.report_trait = row['report_slug'] + ":" + row['trait_name']
        trait.status = row['status']
        trait.trait_name = row['trait_slug']
        trait.is_significant = len(mappings[(mappings.report_name == trait.report_name) & (mappings.trait_slug == trait.trait_name)]) > 0
        user = get_item('user', row['email'])
        trait.user_email = user['user_email']
        trait.save()
