from collections import OrderedDict
from peewee import *
from cendr import get_stripe_keys
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
from gcloud import datastore
ds = datastore.Client(project="andersen-lab")
sys.setdefaultencoding('utf-8')
from cendr.models import *

#=======#
# Setup #
#=======#
current_build = 20160408
reset_db = False

# which services should be updated.
update = ["tajima"] # ["db", "stripe", "gene_table", "tajima"]

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


##########
# TAJIMA #
##########

if "tajima" in update:
    if reset_db:
        db.drop_tables([tajimaD], safe = True)
        db.create_tables([tajimaD], safe = True)
    with open("data/WI_{current_build}.tajima.tsv".format(current_build=current_build), 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        tajima_d = []
        for index, line in enumerate(reader):
            if index > 0:
                for k,v in line.items():
                    if k !='CHROM' and k != 'TajimaD':
                        line[k] = int(v)
                line['TajimaD'] = round(float(line['TajimaD']),3)
                tajima_d.append(line)

    with db.atomic():
      tajimaD.insert_many(tajima_d).execute()


##############
# Gene Table #
##############

if "gene_table" in update:
    if reset_db:
        db.drop_tables([wb_gene], safe = True)
        db.create_tables([wb_gene], safe = True)
    build = "WS245"
    gff_url = "ftp://ftp.wormbase.org/pub/wormbase/releases/{build}/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.{build}.annotations.gff3.gz".format(build = build)
    gff = "c_elegans.{build}.gff".format(build = build)

    if not os.path.exists(gff):
        comm = """curl {gff_url} |\
                  gunzip -kfc |\
                  grep 'WormBase' |\
                  awk '$2 == "WormBase" && $3 == "gene" {{ print }}' > data/{gff}""".format(**locals())
        print(comm)
        print(check_output(comm, shell = True))

    with open(gff, 'r') as f:
        c = 0
        wb_gene_fieldset = [x.name for x in wb_gene._meta.sorted_fields if x.name != "id"]
        gene_set = []
        with db.atomic():
            while True:
                try:
                    line = f.next().strip().split("\t")
                except:
                    break
                if line[0].startswith("#"):
                    continue
                c += 1
                gene = dict([x.split("=") for x in line[8].split(";")])
                gene.update(zip(["CHROM", "start", "end"], [line[0], line[3], line[4]]))
                gene = {k:v for k,v in gene.items() if k in wb_gene_fieldset}
                for i in wb_gene_fieldset:
                    if i not in gene.keys():
                        gene[i] = None
                gene_set.append(gene)
                if c % 5000 == 0:
                    print c, gene["CHROM"], gene["start"]
                    wb_gene.insert_many(gene_set).execute()
                    gene_set = []
            wb_gene.insert_many(gene_set).execute()




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
                print(line["isotype"])
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


##########
# Stripe #
##########
if "stripe" in update:
    # Fetch stripe keys
    stripe_keys = get_stripe_keys()
    stripe.api_key = stripe_keys["secret_key"]
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

