from collections import OrderedDict
from peewee import *
import re
import requests
import json
import datetime
from dateutil.parser import parse
import os
import MySQLdb
import _mysql


#=======#
# Setup #
#=======#
credentials = json.loads(open("credentials.json", 'r').read())
reset_db = True

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

booldict = {"TRUE": True, "FALSE": False, "NA": None, "": None, None: None}

from models import *

with db.atomic():
    if reset_db:
        db.drop_tables([strain, report, trait, trait_value, mapping, snp, order, order_strain], safe = True)
    else:
        db.drop_tables([strain], safe = True)
    db.create_tables([strain, report, trait, trait_value, mapping, snp, order, order_strain], safe=True)


strain_info_join = requests.get(
    "https://raw.githubusercontent.com/AndersenLab/Andersen-Lab-Strains/master/processed/strain_isotype.tsv")

lines = strain_info_join.text.splitlines()

strain_data = []
header = lines[0].split("\t")
for line in lines[1:]:
    strain_info = re.split('\t', line)
    strain_info = [None if x == "NA" else x for x in strain_info]
    l = OrderedDict(zip(header, strain_info))
    l = {k: v for k, v in l.items()}
    l["use"] = booldict[l["use"]]
    l["sequenced"] = booldict[l["sequenced"]]
    l["set_heritability"] = booldict[l["set_heritability"]]
    l["set_1"] = booldict[l["set_1"]]
    l["set_2"] = booldict[l["set_2"]]
    l["set_3"] = booldict[l["set_3"]]
    l["set_4"] = booldict[l["set_4"]]
    if l["latitude"] == "":
        l["latitude"] = None
        l["longitude"] = None
    if l["isolation_date"] is not None:
        l["isolation_date"] = parse(l["isolation_date"])
    for k in l.keys():
        if l[k] == "NA":
            l[k] = None
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
