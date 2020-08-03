# -*- coding: utf-8 -*-
"""

Functions in this script are used to load
information on strains into the sqlite database
used within the CeNDR application

Author: Daniel E. Cook (danielecook@gmail.com)
"""
import requests
import pickle
from functools import wraps
from dateutil import parser
from base.utils.google_sheets import get_google_sheet
from logzero import logger
from base.config import config


def elevation_cache(func):
    """quick and simple cache for lat/lon"""
    fname = ".download/elevation.pkl"
    try:
        func.cache = pickle.load(open(fname, 'rb'))
    except FileNotFoundError:
        func.cache = {}
    @wraps(func)
    def wrapper(*args):
        try:
            return func.cache[args]
        except KeyError:
            logger.info(f"Storing {args}")
            func.cache[args] = result = func(*args)
            if result is not None:
                f = open(fname, 'wb')
                pickle.dump(func.cache, f)
                f.close()
            return result
    return wrapper


@elevation_cache
def fetch_elevations(lat, lon):
    """
        Fetch elevation.

        @lru_cache decorator caches result so we only make one
        call per unique lat/lon result.

    """
    logger.info(f"Fetching {lat}:{lon}")
    elevation_url = f"https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lon}&key={config['ELEVATION_API_KEY']}"
    result = requests.get(elevation_url)
    if result.ok:
        try:
            elevation = result.json()['results'][0]['elevation']
            return elevation
        except KeyError:
            return None


def fetch_andersen_strains():
    """
        Fetches latest strains from
        google sheet database.

        - NA values are converted to NULL
        - Datetime values are parsed
        - Strain sets are concatenated with ','
        - Fetches elevation for each strain
    """
    WI = get_google_sheet(config['ANDERSEN_LAB_STRAIN_SHEET'])
    strain_records = WI.get_all_records()
    # Only take records with a release reported
    strain_records = list(filter(lambda x: x.get('release') not in ['', None, 'NA'], strain_records))
    for n, record in enumerate(strain_records):
        record = {k.lower(): v for k, v in record.items()}
        for k, v in record.items():
            # Set NA to None
            if v in ["NA", '']:
                v = None
                record[k] = v
            if k in ['sampling_date'] and v:
                record[k] = parser.parse(v)
        if record['latitude']:
            # Round elevation
            elevation = fetch_elevations(record['latitude'], record['longitude'])
            if elevation:
                record['elevation'] = round(elevation)
        if n % 50 == 0:
            logger.info(f"Loaded {n} strains")

        # Set issue bools
        record["issues"] = record["issues"] == "TRUE"

        # Fix strain reference
        record['isotype_ref_strain'] = record['isotype_ref_strain'] == "TRUE"
        record['sequenced'] = record['wgs_seq'] == "TRUE"
        
        # set (python built-in) --> strain_set
        record['strain_set'] = record['set']

        # Remove space after comma delimiter
        if record['previous_names']:
            record['previous_names'] = str(record['previous_names']).replace(", ", ",").strip()
        strain_records[n] = record


    return strain_records
