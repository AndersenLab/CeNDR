# -*- coding: utf-8 -*-
from peewee import *
import requests
import os
import StringIO
import csv
import cPickle as pickle
import sys
reload(sys)
import urllib2
from gcloud import datastore
sys.setdefaultencoding('utf-8')
from base.models import *
from base import get_ds

ds = get_ds()

elevation_api = ds.get(ds.key('credential','elevation'))['apiKey']
def fetch_elevation(lat, lng):
    global elevation_api
    query = "https://maps.googleapis.com/maps/api/elevation/json?locations={lat},{lng}&key={elevation_api}"
    result = requests.get(query.format(lat=lat, lng=lng, elevation_api=elevation_api)).json()
    print(result)
    return result['results'][0]['elevation']

def boolify(s):
    if s == 'True':
        return True
    if s == 'False':
        return False
    if s == '':
        return None
    raise ValueError("huh?")

def autoconvert(s):
    for fn in (boolify, int, float):
        try:
            return fn(s)
        except:
            pass
    return s

#=======#
# Setup #
#=======#
current_build = 20160408
reset_db = False

# which services should be updated.
update = ["strains"]  # ["db", "gene_table", "tajima", "homologene", "strains"]

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
    elif k in ["set_1", "set_2", "set_3", "set_4", "reference_strain", "set_heritability", "sequenced"]:
        return booldict[v]
    elif k in ["latitude", "longitude"]:
        return autoconvert(v)
    else:
        return v.encode('utf-8').strip()

table_list = [strain, report, trait, trait_value, mapping]
if "db" in update:
    with db.atomic():
        if reset_db:
            db.drop_tables(table_list, safe=True)
        db.create_tables(table_list, safe=True)


####################
# Homologous Genes #
####################

# Homologene

if "homologene" in update:
    # Load taxon ids
    taxon_ids = pickle.load(open("ancillary/taxon_ids.pickle", "rb"))
    db.drop_tables([homologene], safe=True)
    db.create_tables([homologene], safe=True)

    response = requests.get(
        'https://ftp.ncbi.nih.gov/pub/HomoloGene/current/homologene.data')

    elegans_set = {}

    # In this loop we add the hid (line[0]) if there's a c_elegans gene
    # (line[1]) in the group.
    for line in csv.reader(response.content.splitlines(), delimiter='\t'):
        if line[1] == '6239':
            elegans_set[int(line[0])] = line[3]

    fields = ['HID', 'taxon_id', 'gene_id', 'gene_symbol',
              'protein_gi', 'protein_accession', 'species', 'ce_gene_name']
    gene_list = []

    for line in csv.reader(response.content.splitlines(), delimiter='\t'):
        line = [int(x) if x.isdigit() else x for x in line]
        line.append(taxon_ids[line[1]])
        if line[0] in elegans_set.keys() and line[1] != 6239:
            line.append(elegans_set[line[0]])
            insert_row = dict(zip(fields, line))
            gene_list.append(insert_row)

    with db.atomic():
        for idx in range(0, len(gene_list), 10000):
            print idx, "homologene"
            homologene.insert_many(gene_list[idx:idx + 10000]).execute()

    db.commit()


# WB Orthologs

if "wb_orthologs" in update:
    db.drop_tables([wb_orthologs], safe=True)
    db.create_tables([wb_orthologs], safe=True)
    req = urllib2.Request(
        'ftp://ftp.wormbase.org/pub/wormbase/species/c_elegans/PRJNA13758/annotation/orthologs/c_elegans.PRJNA13758.current_development.orthologs.txt')
    response = urllib2.urlopen(req)
    reader = csv.reader(response, delimiter='\t')

    fields = ['wbid', 'ce_gene_name', 'species',
              'ortholog', 'gene_symbol', 'method']
    gene_list = []

    for line in reader:
        size_of_line = len(line)
        if size_of_line < 2:
            continue
        elif size_of_line == 2:
            wb_gene_header = line
        else:
            new_line = wb_gene_header + line
            new_row = dict(zip(fields, new_line))
            gene_list.append(new_row)

    with db.atomic():
        for idx in range(0, len(gene_list), 10000):
            print idx
            wb_orthologs.insert_many(gene_list[idx:idx + 10000]).execute()

    db.commit()

##############
# Gene Table #
##############

if "gene_table" in update:
    if reset_db:
        db.drop_tables([wb_gene], safe=True)
        db.create_tables([wb_gene], safe=True)
    build = "WS245"
    gff_url = "ftp://ftp.wormbase.org/pub/wormbase/releases/{build}/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.{build}.annotations.gff3.gz".format(
        build=build)
    gff = "c_elegans.{build}.gff".format(build=build)

    if not os.path.exists(gff):
        comm = """curl {gff_url} |\
                  gunzip -kfc |\
                  grep 'WormBase' |\
                  awk '$2 == "WormBase" && $3 == "gene" {{ print }}' > data/{gff}""".format(**locals())

    with open(gff, 'r') as f:
        c = 0
        wb_gene_fieldset = [
            x.name for x in wb_gene._meta.sorted_fields if x.name != "id"]
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
                gene.update(zip(["CHROM", "start", "end"],
                                [line[0], line[3], line[4]]))
                gene = {k: v for k, v in gene.items() if k in wb_gene_fieldset}
                for i in wb_gene_fieldset:
                    if i not in gene.keys():
                        gene[i] = None
                gene_set.append(gene)
                if c % 5000 == 0:
                    print c, gene["CHROM"], gene["start"]
                    wb_gene.insert_many(gene_set).execute()
                    gene_set = []
            wb_gene.insert_many(gene_set).execute()


if "strains" in update:
    strain_info_join = requests.get(
        "https://docs.google.com/spreadsheets/d/1V6YHzblaDph01sFDI8YK_fP0H7sVebHQTXypGdiQIjI/pub?gid=0&single=true&output=tsv")

    lines = list(csv.DictReader(StringIO.StringIO(
        strain_info_join.text), delimiter='\t'))

    strain_data = []

    if reset_db:
        for line in lines:
            l = {k: correct_values(k, v) for k, v in line.items()}
            print(l)  # Can't print characters when running!
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
                l.update({k: v.encode('iso-8859-1') for k, v in l.items() if type(v) == str})

                # fetch elevation
                if l['latitude'] not in ["NA", "", None, "None"]:
                    l['elevation'] = fetch_elevation(l['latitude'], l['longitude'])

                if 'isotype' in l and l['isotype']:
                    strain_set = "|".join(
                        [x["strain"] for x in lines if line["isotype"] == x["isotype"]])
                    previous_names = '|'.join(
                        [x["previous_names"] for x in lines if line["isotype"] == x["isotype"]])
                    try:
                        s = strain.get(strain=l["strain"])
                    except:
                        s = strain()
                    [setattr(s, k, v) for k, v in l.items()]
                    print(s.strain)
                    s.save()
