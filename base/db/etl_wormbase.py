# -*- coding: utf-8 -*-
"""

Functions in this script are used to load
information from wormbase into the 
CeNDR database

Author: Daniel E. Cook (danielecook@gmail.com)
"""

from gtfparse import read_gtf_as_dataframe
from urllib.request import urlretrieve, urlopen
from tempfile import NamedTemporaryFile
from base import WORMBASE_BUILD


url = f"ftp://ftp.wormbase.org/pub/wormbase/releases/{WORMBASE_BUILD}/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.{WORMBASE_BUILD}.canonical_geneset.gtf.gz"

def fetch_gene_gtf():
    """
        This function fetches and parses the canonical geneset GTF
        and yields a dictionary for each row.
    """
    gene_ids = NamedTemporaryFile('wb', suffix=".gz")
    out, err = urlretrieve(url, gene_ids.name)
    gene_ids = read_gtf_as_dataframe(gene_ids.name)
    for row in gene_ids.to_dict('records'):
        yield row
