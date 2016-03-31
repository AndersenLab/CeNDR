from peewee import *
import json
import datetime
import os, sys
import MySQLdb
import _mysql

if (os.getenv('SERVER_SOFTWARE') and
        os.getenv('SERVER_SOFTWARE').startswith('Google App Engine/')):
    db = MySQLDatabase('cegwas', unix_socket='/cloudsql/andersen-lab:cegwas-data', user='root')
else:
    print "connect"
    credentials = json.loads(open("credentials.json",'r').read())
    db =  MySQLDatabase(
      'cegwas_v2',
      **credentials
      )


db.connect()

class strain(Model):
    """
    
        C. Elegans strain information database
    """
    strain = CharField(index=True)
    reference_strain = BooleanField(index = True, null = False)
    isotype = CharField(null=True, index=True)
    previous_names = CharField(null=True)
    warning_message = CharField(null=True)
    sequenced = BooleanField(index = True, null = False)
    source_lab = CharField(null=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    landscape = CharField(null=True)
    substrate = CharField(null=True)
    photo = CharField(null=True)
    isolated_by = CharField(null=True)
    sampled_by = CharField(null=True)
    isolation_date = DateField(null=True)
    isolation_date_comment = CharField(null=True)
    notes = CharField(null=True)
    city = CharField(null=True)
    state = CharField(null=True)
    country = CharField(null=True)
    set_heritability = BooleanField(null=True)
    set_1 = BooleanField(null=True)
    set_2 = BooleanField(null=True)
    set_3 = BooleanField(null=True)
    set_4 = BooleanField(null=True)
    bam_file = CharField(null=True)
    bam_index = CharField(null=True)
    cram_file = CharField(null=True)
    cram_index = CharField(null=True)

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
    charge = CharField(null = False)
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
    release = IntegerField(choices=((0, "public"), (1, "embargo12"), (3, "private")))
    report_hash = CharField(index=True)
    report_name = CharField(index=True, max_length=50, unique=True)
    report_slug = CharField(index=True)
    email = CharField(index=True)
    version = IntegerField(choices=((0, "report 1.0")))  # Version of Report

    def __repr__(self):
        return self.report_name

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
    trait_name = CharField(index = True)
    trait_slug = CharField(index = True)
    status = CharField(null = False)
    submission_date = DateTimeField(default=datetime.datetime.now)
    submission_complete = DateTimeField(null = True)

    class Meta:
        database = db


class trait_value(Model):
    trait = ForeignKeyField(trait)
    strain = ForeignKeyField(strain)
    value = DecimalField()

    class Meta:
        database = db


class mapping(Model):
    """ Results of mappings. Unique on peak IDs and markers. """
    chrom = CharField(index = True)
    pos = IntegerField(index = True)
    report = ForeignKeyField(report)
    trait = ForeignKeyField(trait)
    variance_explained = DecimalField()
    log10p = DecimalField()
    BF = DecimalField()
    interval_start = IntegerField()
    interval_end = IntegerField()
    version = CharField()
    reference = CharField()

    class Meta:
        database = db

class site(Model):
    CHROM = CharField(index = True)
    POS = IntegerField(index = True)
    _ID = CharField()
    REF = CharField()
    ALT = CharField()
    QUAL = FloatField()
    FILTER = CharField()
    ANN = CharField()

    class Meta:
        database = db

class annotation(Model):
    site = ForeignKeyField(site)
    allele = CharField(index=True)
    annotation = CharField(index=True)
    putative_impact = CharField(null=True)
    gene_name = CharField(index=True, null=True)
    gene_id = CharField(index=True, null=True)
    feature_type = CharField(null=True)
    feature_id = CharField(null=True)
    transcript_biotype = CharField(null=True)
    rank_total = CharField(null=True)
    hgvs_c = CharField(null=True)
    hgvs_p = CharField(null=True)
    cdna_position = CharField(null=True)
    cds_position = CharField(null=True)
    protein_position = CharField(null=True)
    distance_to_feature = CharField(null=True)
    errors = CharField(null=True)

    class Meta:
        database = db

class call(Model):
    site = ForeignKeyField(site)
    SAMPLE = CharField(index = True)
    TGT = CharField(index = True)
    FT = CharField(index = True)
    GT = CharField(index = True)



def autoconvert(s):
    for fn in (int, float):
        try:
            return fn(s)
        except ValueError:
            pass
    return s
