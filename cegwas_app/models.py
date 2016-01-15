from peewee import *
import json
import datetime
credentials = json.loads(open("../credentials.json",'r').read())

db = PostgresqlDatabase(
  'andersen',
  **credentials
  )

db.connect()

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

    def __repr__(self):
        return ':'.join([self.isotype, self.strain])

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


def autoconvert(s):
    for fn in (int, float):
        try:
            return fn(s)
        except ValueError:
            pass
    return s
