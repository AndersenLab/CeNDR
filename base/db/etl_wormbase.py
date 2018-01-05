# -*- coding: utf-8 -*-
"""

Functions in this script are used to load
information from wormbase into the 
CeNDR database

Author: Daniel E. Cook (danielecook@gmail.com)
"""

import csv
import gzip
from gtfparse import read_gtf_as_dataframe
from urllib.request import urlretrieve, urlopen
from tempfile import NamedTemporaryFile
from base.constants import WORMBASE_BUILD


# Gene GTF defines biotype, start, stop, etc.
# The GTF does not include locus names (pot-2, etc), so we download them in the get_gene_ids function.
GENE_GTF_URL = f"ftp://ftp.wormbase.org/pub/wormbase/releases/{WORMBASE_BUILD}/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.{WORMBASE_BUILD}.canonical_geneset.gtf.gz"

# Maps wormbase ID to locus name
GENE_IDS_URL = f"ftp://ftp.wormbase.org/pub/wormbase/species/c_elegans/annotation/geneIDs/c_elegans.PRJNA13758.current.geneIDs.txt.gz"

# Lists C. elegans orthologs
ORTHOLOG_URL = f"ftp://ftp.wormbase.org/pub/wormbase/species/c_elegans/PRJNA13758/annotation/orthologs/c_elegans.PRJNA13758.current_development.orthologs.txt"

def get_gene_ids():
    """
        Retrieve mapping between wormbase IDs (WB000...) to locus names.
        Uses the latest IDs by default.
        Gene locus names (e.g. pot-2)
    """
    gene_locus_names_file = NamedTemporaryFile('wb', suffix=".gz")
    out, err = urlretrieve(GENE_IDS_URL, gene_locus_names_file.name)
    return dict([x.split(",")[1:3] for x in gzip.open(out, 'r').read().decode('utf-8').splitlines()])


def fetch_gene_gtf():
    """
        This function fetches and parses the canonical geneset GTF
        and yields a dictionary for each row.
    """
    gene_gtf_file = NamedTemporaryFile('wb', suffix=".gz")
    out, err = urlretrieve(GENE_GTF_URL, gene_gtf_file.name)
    gene_gtf = read_gtf_as_dataframe(gene_gtf_file.name)

    gene_ids = get_gene_ids()
    # Add locus column
    gene_gtf = gene_gtf.assign(locus_name=[gene_ids.get(x) for x in gene_gtf.gene_id])

    for row in gene_gtf.to_dict('records'):
        yield row

def fetch_orthologs():
    """
        Fetches orthologs from wormbase; Stored in the homolog table.
    """
    orthologs_file = NamedTemporaryFile('wb', suffix=".txt")
    out, err = urlretrieve(ORTHOLOG_URL , orthologs_file.name)
    csv_out = list(csv.reader(open(out, 'r'), delimiter='\t'))

    fields = ['wbid', 'ce_gene_name', 'species',
              'ortholog', 'gene_symbol', 'method']
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