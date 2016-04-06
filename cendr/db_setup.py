from collections import OrderedDict
from peewee import *
import re
import requests
import json
import datetime
from dateutil.parser import parse
import os
import StringIO
import csv
import MySQLdb
import _mysql
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

#=======#
# Setup #
#=======#
credentials = json.loads(open("credentials.json", 'r').read())
reset_db = False

if (os.getenv('SERVER_SOFTWARE') and
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    db = MySQLDatabase('cegwas', unix_socket='/cloudsql/andersen-lab:cegwas-data', user='root')
else:
    credentials = json.loads(open("credentials.json",'r').read())
    db =  MySQLDatabase(
      'cegwas',
      **credentials
      )


db.connect()

booldict = {"TRUE": True, "FALSE": False, "NA": None, "#N/A": None, "": None, None: None, 1: True, 0: False, "1": True, "0": False}

def correct_values(k, v):
    if v == "NA":
        return None
    elif k in ["set_1","set_2","set_3","set_4", "reference_strain", "set_heritability", "sequenced"]:
        return booldict[v]
    elif k in ["latitude", "longitude"]:
        return autoconvert(v)
    else:
        return v.encode('utf-8').strip()

from models import *
with db.atomic():
    if reset_db:
        db.drop_tables([strain, report, trait, trait_value, mapping, order, order_strain], safe = True)
    db.create_tables([strain, report, trait, trait_value, mapping, order, order_strain], safe=True)

strain_info_join = requests.get(
    "https://raw.githubusercontent.com/AndersenLab/Andersen-Lab-Strains/master/processed/strain_isotype.tsv")

lines = csv.DictReader(StringIO.StringIO(strain_info_join.text), delimiter='\t')

strain_data = []

if reset_db:
    for line in lines:
        l = {k: correct_values(k, v) for k, v in line.items()}
        print l # Can't print characters when running!
        if l["isotype"] != "":
            strain_data.append(l)

    with db.atomic():
        strain.insert_many(strain_data).execute()

    try:
        db.execute_sql("""
        CREATE VIEW report_trait AS SELECT report.id AS report_id, report.report_name, report.report_slug, trait.id AS traitID , trait.trait_name, trait.trait_slug, report.email, trait.status, trait.submission_date, trait.submission_complete, report.release FROM report JOIN trait ON trait.report_id = report.id;
        CREATE VIEW report_trait_value AS (SELECT *  FROM trait_value JOIN report_trait ON report_trait.traitID = trait_value.trait_id)
        CREATE VIEW report_trait_strain_value AS (SELECT report_name, report_slug, trait_name, trait_slug, strain_id, value, email, submission_date, submission_complete, `release`, strain.* FROM report_trait_value JOIN strain ON strain_id = strain.id);

        """)
    except:
        pass
else:
    with db.atomic():
        for line in lines:
            l = {k: correct_values(k, v) for k, v in line.items()}
            print line["strain"]
            try:
                s = strain.get(strain = l["strain"])
                [setattr(s, k, v) for k,v in l.items()]
                s.save()
            except:
                s = strain()
                [setattr(s, k, v) for k,v in l.items()]
                s.save()