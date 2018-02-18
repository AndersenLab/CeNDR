#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Site utility functions.

"""
import arrow
import pandas as pd
import datetime
import pandas as pd
from logzero import logger
from base.application import cache
from base.utils.gcloud import query_item, google_analytics

@cache.cached(timeout=60*60*24*7, key_prefix='visits')
def get_weekly_visits():
    """
        Get the number of weekly visitors

        Cached weekly
    """
    ga = google_analytics()
    response = ga.reports().batchGet(
        body={
            'reportRequests': [
                {
                    'viewId': '117392266',
                    'dateRanges': [{'startDate':'2015-01-01', 'endDate': arrow.now().date().isoformat()}],
                    'metrics': [{'expression': 'ga:sessions'}],
                    'dimensions': [{'name': 'ga:year'}, {'name': 'ga:week'}],
                    'orderBys': [{"fieldName": "ga:sessions", "sortOrder": "DESCENDING"}],
                    'pageSize': 10000
                }]
        }
    ).execute()
    out = []
    for row in response['reports'][0]['data']['rows']:
        ymd = f"{row['dimensions'][0]}-W{row['dimensions'][1]}-0"
        date = datetime.datetime.strptime(ymd, "%Y-W%W-%w")
        out.append({'date': date, 'count': row['metrics'][0]['values'][0]})
    df = pd.DataFrame(out) \
           .sort_values('date') \
           .reindex_axis(['date', 'count'], axis=1)
    df['count'] = df['count'].astype(int)
    df['count'] = df['count'].dropna().cumsum()
    return df


@cache.cached(timeout=60*60*24, key_prefix='mappings')
def get_mappings_summary():
    """
        Generates the cumulative sum of reports and traits mapped.

        Cached daily
    """
    traits = query_item('trait')

    traits = pd.DataFrame.from_dict(traits)
    traits.created_on = traits.apply(lambda x: arrow.get(str(x['created_on'])[:-6]).date().isoformat(), axis=1)

    trait_df = traits.groupby('created_on').size().reset_index(name='traits')
    report_df = traits[['report_slug', 'created_on']].drop_duplicates().groupby('created_on').size().reset_index(name='reports')
    df = pd.merge(report_df, trait_df, how='outer').fillna(0).sort_values('created_on')
    df.reports = df.reports.cumsum()
    df.traits = df.traits.cumsum()
    return df


@cache.cached(timeout=60*60*24*7, key_prefix='n_mapping_users')
def get_unique_users():
    """
        Counts the number of unique mapping users

        Cached weekly
    """
    users = query_item('user', projection=['user_email'])
    return len(users)



def get_latest_public_mappings():
    """
        Returns the 5 most recent mappings
    """
    recent_traits = list(query_item('trait',
                                    filters=[('is_public', '=', True)],
                                    projection=('report_slug', 'trait_name', '-created_on',),
                                    limit=5))
    return recent_traits
