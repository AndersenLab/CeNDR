# -*- coding: utf-8 -*-
"""

Functions in this script are used to load
information on strains into the sqlite database
used within the CeNDR application

Author: Daniel E. Cook (danielecook@gmail.com)
"""
from dateutil import parser
from base.utils.google_sheets import get_google_sheet


def fetch_andersen_strains():
    """
        Fetches latest strains from
        google sheet database.

        - NA values are converted to NULL
        - Datetime values are parsed
        - Strain sets are concatenated with ','
    """
    WI = get_google_sheet("WI")
    strain_records = WI.get_all_records()
    strain_records = list(filter(lambda x: x.get('isotype') not in ['', None, 'NA'], strain_records))
    for record in strain_records:
        set_list = ','.join([set_name.split("_")[1] for set_name, set_val in record.items() 
                             if 'set_' in set_name and set_val == "TRUE"])
        record['sets'] = set_list
        for k, v in record.items():
            # Set NA to None
            if v in ["NA", '']:
                v = None
                record[k] = v
            if k in ['isolation_date'] and v:
                record[k] = parser.parse(v)
        # Create set record
    return strain_records