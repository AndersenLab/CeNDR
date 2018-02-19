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


@cache.cached(timeout=60*60*24, key_prefix='get_reports_by_date')
def get_reports_by_date():
    """
        Gets the number of reports submitted by date
    """
    traits = pd.DataFrame.from_dict(query_item('trait'))
    # Convert datetime to just date
    traits.created_on = traits.created_on.apply(lambda x: arrow.get(x).date().isoformat())
    report_df = traits[['report_slug', 'created_on']].drop_duplicates().groupby('created_on').size().reset_index(name='count')
    report_df = report_df.rename(index=str, columns={'created_on':'date', 'reports': 'count'})
    last_year_dates = pd.DataFrame({'date':pd.date_range(arrow.now().shift(days=-365).date(), arrow.now().date())})
    last_year_dates.date = last_year_dates.date.apply(lambda x: x.date().isoformat())
    report_df = pd.merge(last_year_dates, report_df, how='left').fillna(0)
    report_df['count'] = report_df['count'].astype(int)
    report_df = report_df[['date', 'count']].sort_values('date')
    return report_df


def get_latest_public_mappings():
    """
        Returns the 5 most recent mappings
    """
    recent_traits = list(query_item('trait',
                                    filters=[('is_public', '=', True)],
                                    projection=('report_slug', 'trait_name', 'created_on',),
                                    limit=5))
    for trait in recent_traits:
        trait['created_on'] = arrow.get(str(trait['created_on'])[:-6])
    return recent_traits
