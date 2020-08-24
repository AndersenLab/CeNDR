# -*- coding: utf-8 -*-
"""

Functions in this script are used to load
information from wormbase into the
CeNDR database

Author: Daniel E. Cook (danielecook@gmail.com)
"""

import csv
import gzip
from logzero import logger
from gtfparse import read_gtf_as_dataframe
from base.utils.bio import arm_or_center
from base.constants import URLS, CHROM_NUMERIC

# https://github.com/phil-bergmann/2016_DLRW_brain/blob/3f69c945a40925101c58a3d77c5621286ad8d787/brain/data.py


def get_gene_ids(gene_ids_fname: str):
    """
        Retrieve mapping between wormbase IDs (WB000...) to locus names.
        Uses the latest IDs by default.
        Gene locus names (e.g. pot-2)
    """
    results = [x.split(",")[1:3] for x in gzip.open(gene_ids_fname, 'r').read().decode('utf-8').splitlines()]
    return dict(results)


def fetch_gene_gtf(gtf_fname: str, gene_ids_fname: str):
    """
        LOADS wormbase_gene
        This function fetches and parses the canonical geneset GTF
        and yields a dictionary for each row.
    """
    gene_gtf = read_gtf_as_dataframe(gtf_fname)
    gene_ids = get_gene_ids(gene_ids_fname)

    # Add locus column
    # Rename seqname to chrom
    gene_gtf = gene_gtf.rename({'seqname': 'chrom'}, axis='columns')
    gene_gtf = gene_gtf.assign(locus=[gene_ids.get(x) for x in gene_gtf.gene_id])
    gene_gtf = gene_gtf.assign(chrom_num=[CHROM_NUMERIC[x] for x in gene_gtf.chrom])
    gene_gtf = gene_gtf.assign(pos=(((gene_gtf.end - gene_gtf.start)/2) + gene_gtf.start).map(int))
    gene_gtf.frame = gene_gtf.frame.apply(lambda x: x if x != "." else None)
    gene_gtf.exon_number = gene_gtf.exon_number.apply(lambda x: x if x != "" else None)
    gene_gtf['arm_or_center'] = gene_gtf.apply(lambda row: arm_or_center(row['chrom'], row['pos']), axis=1)
    for row in gene_gtf.to_dict('records'):
        yield row


def fetch_gene_gff_summary(gff_fname: str):
    """
        LOADS wormbase_gene_summary
        This function fetches data for wormbase_gene_summary;
        It's a condensed version of the wormbase_gene_table
        constructed for convenience.
    """
    WB_GENE_FIELDSET = ['ID', 'biotype', 'sequence_name', 'chrom', 'start', 'end', 'locus']

    with gzip.open(gff_fname) as f:
        idx = 0
        gene_count = 0
        for line in f:
            idx += 1
            if line.decode('utf-8').startswith("#"):
                continue
            line = line.decode('utf-8').strip().split("\t")
            if idx % 1000000 == 0:
                logger.info(f"Processed {idx} lines;{gene_count} genes; {line[0]}:{line[4]}")
            if 'WormBase' in line[1] and 'gene' in line[2]:
                gene = dict([x.split("=") for x in line[8].split(";")])
                gene.update(zip(["chrom", "start", "end"],
                                [line[0], line[3], line[4]]))
                gene = {k.lower(): v for k, v in gene.items() if k in WB_GENE_FIELDSET}

                # Change add chrom_num
                gene['chrom_num'] = CHROM_NUMERIC[gene['chrom']]
                gene['start'] = int(gene['start'])
                gene['end'] = int(gene['end'])
                # Annotate gene with arm/center
                gene_pos = int(((gene['end'] - gene['start'])/2) + gene['start'])
                gene['arm_or_center'] = arm_or_center(gene['chrom'], gene_pos)
                if 'id' in gene.keys():
                    gene_count += 1
                    gene_id_type, gene_id = gene['id'].split(":")
                    gene['gene_id_type'], gene['gene_id'] = gene['id'].split(":")

                    del gene['id']
                    yield gene


def fetch_orthologs(orthologs_fname: str):
    """
        LOADS (part of) homologs
        Fetches orthologs from wormbase; Stored in the homolog table.
    """
    csv_out = list(csv.reader(open(orthologs_fname, 'r'), delimiter='\t'))

    for line in csv_out:
        size_of_line = len(line)
        if size_of_line < 2:
            continue
        elif size_of_line == 2:
            wb_id, locus_name = line
        else:
            yield {'gene_id': wb_id,
                   'gene_name': locus_name,
                   'homolog_species': line[0],
                   'homolog_taxon_id': None,
                   'homolog_gene': line[2],
                   'homolog_source': line[3],
                   'is_ortholog': line[0] == 'Caenorhabditis elegans'}
