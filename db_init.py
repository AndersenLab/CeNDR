from cendr import get_db
from cendr.models import *
import os
from subprocess import check_output

db = get_db()

build = "WS258"
gff_url = "ftp://ftp.wormbase.org/pub/wormbase/releases/{build}/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.{build}.annotations.gff3.gz".format(
    build=build)
gff = "c_elegans.{build}.gff".format(build=build)

comm = """curl {gff_url} > {gff}.gz && 
          gunzip -kfc {gff}.gz |\
          grep 'WormBase' |\
          awk '$2 == "WormBase" && $3 == "gene" {{ print }}' > {gff}""".format(**locals())

check_output(comm, shell=True)

with open(gff, 'r') as f:
    c = 0
    wb_gene_fieldset = [
        x.name for x in wb_gene._meta.sorted_fields if x.name != "id"]
    gene_set = []
    with db.atomic() as transaction:
        try:
            db.drop_tables([wb_gene], safe=True)
            db.create_tables([wb_gene], safe=True)
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
                    wb_gene.insert_many(gene_set).execute()
                    gene_set = []
            wb_gene.insert_many(gene_set).execute()
        except:
            db.rollback()
