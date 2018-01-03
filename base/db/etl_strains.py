# -*- coding: utf-8 -*-
"""

Functions in this script are used to load
information on strains into the sqlite database
used within the CeNDR application

Author: Daniel E. Cook (danielecook@gmail.com)
"""
import requests
from functools import lru_cache
from dateutil import parser
from base.utils.google_sheets import get_google_sheet
from base.utils.gcloud import get_item
from logzero import logger
ELEVATION_API_KEY=elevation_api_key = get_item('credential', 'elevation').get('apiKey')


@lru_cache(maxsize=32)
def fetch_elevations(lat, lon):
    """
        Fetch elevation
    """
    result = requests.get(f"https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={ELEVATION_API_KEY}")
    if result.ok:
        elevation = result.json()['results'][0]['elevation']
        return elevation


def fetch_andersen_strains():
    """
        Fetches latest strains from
        google sheet database.

        - NA values are converted to NULL
        - Datetime values are parsed
        - Strain sets are concatenated with ','
        - Fetches elevation for each strain
    """
    WI = get_google_sheet("WI")
    strain_records = WI.get_all_records()
    strain_records = list(filter(lambda x: x.get('isotype') not in ['', None, 'NA'], strain_records))
    for n, record in enumerate(strain_records):
        set_list = ','.join([set_name.split("_")[1] for set_name, set_val in record.items() 
                             if 'set_' in set_name and set_val == "TRUE"])
        record['sets'] = set_list
        latlon_set = []
        for k, v in record.items():
            # Set NA to None
            if v in ["NA", '']:
                v = None
                record[k] = v
            if k in ['isolation_date'] and v:
                record[k] = parser.parse(v)
        if record['latitude']:
            record['elevation'] = fetch_elevations(record['latitude'], record['longitude'])
        if n % 50 == 0:
            logger.info(f"Loaded {n} strains")
    return strain_records