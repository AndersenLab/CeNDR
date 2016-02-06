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
    db = MySQLDatabase('cegwas', unix_socket='/cloudsql/andersen-lab:cegwas-sql', user='root')
else:
    credentials = json.loads(open("credentials.json",'r').read())
    db =  MySQLDatabase(
      'cegwas',
      **credentials
      )


db.connect()

booldict = {"TRUE": True, "FALSE": False, "NA": None, "":None, None: None}

#=======================#
# Generate strain table #
#=======================#

class strain(Model):
    """
        C. Elegans strain information database
    """
    strain = CharField(index=True)
    isotype = CharField(null=True, index=True)
    reference_strain = CharField(index=True, null=True)
    warning_message = CharField(null=True)
    use = BooleanField()
    sequenced = BooleanField()
    previous_names = CharField(null=True)
    source_lab = CharField(null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    landscape = CharField(null=True)
    substrate = CharField(null=True)
    isolated_by = CharField(null=True)
    isolation_date = DateField(null=True)
    isolation_date_comment = CharField(null=True)
    isolation = CharField(null=True)
    location = CharField(null=True)
    address = CharField(null=True)
    city = CharField(null=True)
    state = CharField(null=True)
    country = CharField(null=True)
    set_heritability = BooleanField(null=True)
    set_1 = BooleanField(null=True)
    set_2 = BooleanField(null=True)
    set_3 = BooleanField(null=True)
    set_4 = BooleanField(null=True)

    class Meta:
        database = db



class order(Model):
    price = FloatField()
    stripeToken = CharField(index = True)
    stripeShippingName = CharField(null = False)
    stripeEmail = CharField(null = False)
    stripeShippingAddressLine1 = CharField(null = False)
    stripeShippingAddressCity = CharField(null = False)
    stripeShippingAddressState = CharField(null = False)
    stripeShippingAddressZip = IntegerField(null = False)
    stripeShippingAddressCountry = CharField(null = False)
    stripeShippingAddressCountryCode = CharField(null = False)

    # Billing
    stripeBillingName = CharField(null = False)
    stripeBillingAddressLine1 = CharField(null = False)
    stripeBillingAddressCity = CharField(null = False)
    stripeBillingAddressState = CharField(null = False)
    stripeBillingAddressZip = IntegerField(null = False)
    stripeBillingAddressCountry = CharField(null = False)
    stripeBillingAddressCountryCode = CharField(null = False)

    order_time = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db


class order_strain(Model):
    order = ForeignKeyField(order)
    strain = ForeignKeyField(strain)


    class Meta:
        database = db


class report(Model):
    """
        Reports
    """
    release = IntegerField(choices=((0, "public"), (1, "embargo6"), (2, "embargo12"), (3, "private")))
    report_name = CharField(index=True, max_length=50, unique=True)
    report_slug = CharField(index=True)
    email = CharField(index=True)
    submission_date = DateTimeField(default=datetime.datetime.now)
    submission_complete = DateTimeField(null = True)
    version = IntegerField(choices=((0, "report 1.0")))  # Version of Report

    class Meta:
        database = db


class snp(Model):
    """
        Table of strain genotypes
    """
    strain = ForeignKeyField(strain)
    chrom = CharField(index=True)
    pos = IntegerField(index=True)
    allele = IntegerField()
    allele_base = CharField()
    version = IntegerField(choices=((0, "snps 2.0")))  # Version of Snpset

    class Meta:
        database = db


class trait(Model):
    """ 
        Initially, trait data only contains:
          -report
          -strain
          -name (trait name)
          -value (value of trait)
    """
    report = ForeignKeyField(report)
    strain = ForeignKeyField(strain)
    name = CharField(index=True)
    value = DecimalField()

    class Meta:
        database = db


class mapping(Model):

    """ Results of mappings. Unique on peak IDs and markers. """
    trait = ForeignKeyField(trait)
    snp = ForeignKeyField(snp)
    variance_explained = DecimalField()
    log10p = DecimalField()
    BF = DecimalField()
    significant = BooleanField()
    interval_start = IntegerField()
    interval_end = IntegerField()

    class Meta:
        database = db


if reset_db:
    db.drop_tables([strain, trait, report, mapping, snp, order, order_strain], safe=True)

db.drop_tables([strain], safe=True)
db.create_tables([strain, report, trait, mapping, snp, order, order_strain], safe=True)


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

db.execute_sql("""
CREATE VIEW report_trait AS SELECT report.report_name, report.report_slug, report.email, report.submission_date, report.submission_complete, report.release, trait.strain_id, trait.name, trait.value FROM report JOIN trait ON trait.report_id = report.id;
CREATE VIEW report_trait_strain AS (SELECT * FROM strain JOIN report_trait ON report_trait.strain_id = strain.id)
""")
