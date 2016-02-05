from peewee import *
import json
import datetime
import os
import MySQLdb
import _mysql
from google.appengine.api import rdbms
credentials = json.loads(open("credentials.json",'r').read())

class AppEngineDatabase(MySQLDatabase):
    def _connect(self, database, **kwargs):
        if 'instance' not in kwargs:
            raise ImproperlyConfigured('Missing "instance" keyword to connect to database')
        return rdbms.connect(database=database, **kwargs)

if (os.getenv('SERVER_SOFTWARE') and
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')) and 1 == 0:
    db = MySQLDatabase('cegwas', unix_socket='/cloudsql/andersen-lab:cegwas-db', user='root')
else:
    db =  MySQLDatabase(
      'cegwas',
      **credentials
      )

db.connect()

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

    def __repr__(self):
        return self.strain

    def list_sets(self):
        set_list = []
        if self.set_heritability == True:
            set_list.append("set_heritability")
        if self.set_1 == True:
            set_list.append("set_1")
        if self.set_2 == True:
            set_list.append("set_2")
        if self.set_3 == True:
            set_list.append("set_3")
        if self.set_4 == True:
            set_list.append("set_4")
        return set_list

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
