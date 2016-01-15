from collections import OrderedDict
from peewee import *
import re
import requests
import json
import datetime

#=======#
# Setup #
#=======#
credentials = json.loads(open("credentials.json", 'r').read())
reset_db = True

#==========#
# Database #
#==========#

db = PostgresqlDatabase(
    'andersen',
    **credentials
)

db.connect()


booldict = {"TRUE": True, "FALSE": False}

#=======================#
# Generate strain table #
#=======================#


class strain(Model):
    """
        C. Elegans strain information database
    """
    strain = CharField(index=True)
    isotype = CharField(null=True, index=True)
    longitude = FloatField(null=True)
    latitude = FloatField(null=True)
    isolation = CharField(null=True)
    location = CharField(null=True)
    prev_names = CharField(null=True)
    warning_msg = CharField(null=True)
    sequenced = BooleanField()

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
    db.drop_tables([trait, report, mapping, snp], safe=True, cascade=True)

db.drop_tables([strain], safe=True)
db.create_tables([strain, report, trait, mapping, snp], safe=True)

header = ["strain", "isotype", "longitude", "latitude", "isolation", "location", "prev_names",
          "warning_msg", "sequenced"]

strain_info_join = requests.get(
    "https://raw.githubusercontent.com/AndersenLab/Andersen-Lab-Strains/master/processed/strain_info_join.tsv")

lines = strain_info_join.text.splitlines()

strain_data = []
with db.atomic():
    for line in lines[1:]:
        strain_info = re.split('\t', line)
        l = OrderedDict(zip(header, strain_info))
        l = {k: v for k, v in l.items()}
        l["sequenced"] = booldict[l["sequenced"]]
        for k in l.keys():
            if l[k] == "NA":
                l[k] = None
        strain_data.append(l)

with db.atomic():
    strain.insert_many(strain_data).execute()
