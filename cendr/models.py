from peewee import *
import json
import datetime
import os, sys
import MySQLdb
import _mysql

current_build = 20160408

# Fetch credentials
from gcloud import datastore
ds = datastore.Client(project="andersen-lab")

if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
    dbname = "cegwas_v2" # don't remove, imported elsewhere.
    db = MySQLDatabase(dbname, unix_socket='/cloudsql/andersen-lab:cegwas-data', user='root')
else:
    credentials = dict(ds.get(ds.key("credential", "cegwas-data")))
    dbname = "cegwas_v2" # don't remove, imported elsewhere.
    db =  MySQLDatabase(
      dbname,
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
    set_divergent = BooleanField(null=True)
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
        if self.set_divergent == True:
            set_list.append("set_divergent")
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


class mapping_correlation(Model):
    report = ForeignKeyField(report)
    trait = ForeignKeyField(trait)
    CHROM = CharField(index = True)
    POS = IntegerField(index = True)
    gene_id = CharField(index = True)
    alt_allele = IntegerField() # Number of alternative alleles.
    num_strains = IntegerField()
    correlation = FloatField()

    class Meta:
        database = db


class WI(Model):
    CHROM = CharField(max_length=5)
    POS = IntegerField()
    _ID = CharField()
    REF = CharField()
    ALT = CharField()
    QUAL = FloatField()
    FILTER = CharField()
    GT = CharField(max_length=8000)
    allele = CharField(max_length=3)
    annotation = CharField()
    putative_impact = CharField(max_length=40)
    gene_name = CharField(null=True, max_length=40)
    gene_id = CharField(null=True, max_length=40)
    feature_type = CharField(null=True, max_length=40)
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
    INDEL = BooleanField()

    class Meta:
        database = db
        db_table = "WI_20160408"
        indexes = (
            (('CHROM', 'POS', 'FILTER', 'feature_id', 'annotation','gene_id', 'gene_name', 'putative_impact'), False),
            )

class intervals(Model):
    CHROM = CharField(index = True, max_length=5)
    BIN_START = IntegerField(index=True)
    BIN_END = IntegerField(index=True)
    N_VARIANTS = IntegerField(default = 0)
    ALL_Total = IntegerField(default = 0)
    ALL_protein_coding = IntegerField(default = 0)
    ALL_ncRNA = IntegerField(default = 0)
    ALL_miRNA = IntegerField(default = 0)
    ALL_piRNA = IntegerField(default = 0)
    ALL_tRNA = IntegerField(default = 0)
    ALL_lincRNA = IntegerField(default = 0)
    ALL_rRNA = IntegerField(default = 0)
    ALL_scRNA = IntegerField(default = 0)
    ALL_snoRNA = IntegerField(default = 0)
    ALL_snRNA = IntegerField(default = 0)
    ALL_asRNA = IntegerField(default = 0)
    ALL_pseudogene = IntegerField(default = 0)
    MODERATE_Total = IntegerField(default = 0)
    MODERATE_protein_coding = IntegerField(default = 0)
    MODERATE_pseudogene = IntegerField(default = 0)
    HIGH_Total = IntegerField(default = 0)
    HIGH_protein_coding = IntegerField(default = 0)
    HIGH_pseudogene = IntegerField(default = 0)

    class Meta:
        database = db
        db_table = "WI_{current_build}_intervals".format(current_build = current_build)
        indexes = (
            (('CHROM', 'BIN_START', 'BIN_END'), True),
            )

class tajimaD(Model):
    CHROM = CharField(index=True)
    BIN_START = IntegerField(index=True)
    BIN_END = IntegerField(index=True)
    N_Sites = IntegerField(index=True)
    N_SNPs = IntegerField(index=True)
    TajimaD = FloatField(index=True)

    class Meta:
        database = db
        db_table = "WI_{current_build}_tajimad".format(current_build = current_build)


class wb_gene(Model):
    CHROM = CharField(index = True, max_length = 5)
    start = IntegerField(index = True)
    end = IntegerField(index = True)
    Name = CharField(index = True)
    sequence_name = CharField(index = True)
    biotype = CharField(index = True)
    locus = CharField(index = True, default = None)

    class Meta:
        database = db

class homologene(Model):
    HID = IntegerField(index=True)
    taxon_id = IntegerField(index=True)
    gene_id = IntegerField(index=True) # entrez
    gene_symbol = CharField(index=True)
    protein_gi = IntegerField(index=True)
    protein_accession = CharField(index=True)
    species = CharField(index=True)
    ce_gene_name = CharField(default=False)
    class Meta:
        database = db

class wb_orthologs(Model):
    wbid = CharField(index=True)
    ce_gene_name = CharField(index=True)
    species = CharField(index=True)
    ortholog = CharField(index=True)
    gene_symbol = CharField(index=True)
    method = CharField(index=True) # Method used to assign ortholog
    class Meta:
        database = db

def autoconvert(s):
    for fn in (int, float):
        try:
            return fn(s)
        except ValueError:
            pass
    return s
