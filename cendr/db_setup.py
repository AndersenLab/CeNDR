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
import stripe
from gcloud import datastore
ds = datastore.Client(project="andersen-lab")
sys.setdefaultencoding('utf-8')
from models import *

#=======#
# Setup #
#=======#
reset_db = False

# which services should be updated.
update = ["stripe"] # ["db", "stripe"]

# Fetch stripe keys
if (os.getenv('SERVER_SOFTWARE') and
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    stripe_keys = ds.get(ds.key("credential", "stripe_live"))
else:
    stripe_keys = ds.get(ds.key("credential", "stripe_test"))
    credentials = json.loads(open("credentials.json",'r').read())

stripe.api_key = stripe_keys["secret_key"]

booldict = {"TRUE": True,
            "FALSE": False,
            "NA": None, 
            "#N/A": None, 
            "": None, 
            None: None, 
            1: True, 
            0: False, 
            "1": True, 
            "0": False}

def correct_values(k, v):
    if v == "NA":
        return None
    elif k in ["set_1","set_2","set_3","set_4", "reference_strain", "set_heritability", "sequenced"]:
        return booldict[v]
    elif k in ["latitude", "longitude"]:
        return autoconvert(v)
    else:
        return v.encode('utf-8').strip()

table_list = [strain, report, trait, trait_value, mapping]
if "db" in update:
    with db.atomic():
        if reset_db:
            db.drop_tables(table_list, safe = True)
        db.create_tables(table_list, safe = True)

strain_info_join = requests.get(
    "https://raw.githubusercontent.com/AndersenLab/Andersen-Lab-Strains/master/processed/strain_isotype_full.tsv")

lines = list(csv.DictReader(StringIO.StringIO(strain_info_join.text), delimiter='\t'))

strain_data = []

if reset_db:
    for line in lines:
        l = {k: correct_values(k, v) for k, v in line.items()}
        print l # Can't print characters when running!
        if l["isotype"] != "":
            strain_data.append(l)

    if "db" in update:
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
        #print stripe.Product.all()

    with db.atomic():
        for line in lines:
            l = {k: correct_values(k, v) for k, v in line.items()}
            # Setup data for stripe.
            strain_set = "|".join([x["strain"] for x in lines if line["isotype"] == x["isotype"]])
            previous_names = '|'.join([x["previous_names"] for x in lines if line["isotype"] == x["isotype"]])
            try:
                s = strain.get(strain = l["strain"])
            except:
                s = strain()
            [setattr(s, k, v) for k,v in l.items()]
            if "db" in update:
                s.save()
            # Add Stripe Products
            if l["reference_strain"] and l["isotype"] != "NA" and l["isotype"] != "" and "stripe" in update:
                try:
                    # Try to update product
                    product = stripe.Product.retrieve(l["isotype"])
                    product.id = l["isotype"]
                    product.name = l["isotype"]
                    product.caption = "Strain: {strain}; Isotype: {isotype}".format(strain = line["strain"], isotype = line["isotype"])
                    product.metadata["isotype"] = l["isotype"]
                    product.metadata["strain_set"] = strain_set
                    product.metadata["previous_names"] = previous_names 
                    product.save()
                except:
                    # If product does not exist, create it.
                    product = stripe.Product.create(
                        id=line["isotype"],
                        name=line["isotype"],
                        caption="Strain: {strain}; Isotype: {isotype}".format(strain = line["strain"], isotype = line["isotype"]),
                        metadata={'isotype': line["isotype"],
                                  'strain_set': strain_set,
                                  'previous_names': previous_names},
                    )
                # Create SKU (Stock keeping unit)
                try:
                    # Try to update product
                    sku = stripe.SKU.retrieve(l["strain"])
                    sku.currency = "usd"
                    sku.inventory = {"type": "infinite"}
                    sku.product = line["isotype"]
                    sku.price = 1000
                except:
                    sku = stripe.SKU.create(
                        id = line["strain"],
                        currency = "usd",
                        inventory = {"type": "infinite"},
                        product = line["isotype"],
                        price = 1000
                        )
                print line["strain"]

# Add Strain Sets
if "stripe" in update:
    for i in ["1","2","3","divergent"]:
        print i
        set_name = "set_" + i 
        if set_name == "set_divergent":
            price = 10000
            caption = "12 strains"
        else:
            price = 40000
            caption = "48 strains"
        strain_list = ','.join(sorted([str(x) for x in list(strain.filter(getattr(strain, set_name) == True).execute())]))
        try:
            product = stripe.Product.create(
            id=set_name,
            name=set_name,
            description=strain_list,
            caption=caption
            )
        except:
            product = stripe.Product.retrieve(set_name)
            product.id = set_name
            product.name = set_name
            product.description = strain_list
            product.caption=caption
            product.save()
        try:
            sku = stripe.SKU.create(
                id = set_name,
                currency = "usd",
                inventory = {"type": "infinite"},
                product = product.name,
                price = price
            )
        except:
            sku = stripe.SKU.retrieve(set_name)
            sku.id = set_name
            sku.currency = "usd"
            sku.inventory = {"type": "infinite", "quantity": None, "value": None}
            sku.price = price
            sku.save()

