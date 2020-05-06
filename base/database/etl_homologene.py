# -*- coding: utf-8 -*-
"""

Fetches the homologene database

Author: Daniel E. Cook (danielecook@gmail.com)
"""
import re
import tarfile
import csv
import requests
from urllib.request import urlretrieve
from tempfile import NamedTemporaryFile
from base.models import wormbase_gene_summary_m
from base.constants import URLS


def fetch_taxon_ids():
    """
        Downloads mapping of taxon-ids to species names.
    """
    taxon_file = NamedTemporaryFile(suffix='tar')
    out, err = urlretrieve(URLS.TAXON_ID_URL, taxon_file.name)
    tar = tarfile.open(out)
    # Read names file
    names_dmp = tar.extractfile('names.dmp')
    names_dmp = names_dmp.read().decode('utf-8').splitlines()
    lines = [re.split(r"\t\|[\t]?", x) for x in names_dmp]
    taxon_ids = {int(l[0]): l[1] for l in lines if l[3] == 'scientific name'}
    return taxon_ids


def fetch_homologene():
    """
        Download the homologene database and load

        Output dictionary has the following structure:

         {
          'hid': '2188',
          'taxon_id': '7165'
          'gene_id': '1280005',
          'ce_gene_name': 'Y97E10AL.3',
          'gene_symbol': 'AgaP_AGAP009047',
          'protein_accession': 'XP_319799.4',
          'protein_gi': '158299762',
          'species': 'Anopheles gambiae',
          }

          * hid = Homolog ID: Assigned to multiple lines; a group genes that are homologous
          * taxon_id = NCBI taxonomic ID
          * gene_id = NCBI Entrez ID
          * gene_symbol = Gene Symbol
          * species = species name
    """
    response = requests.get(URLS.HOMOLOGENE_URL)
    response_csv = list(csv.reader(response.content.decode('utf-8').splitlines(), delimiter='\t'))

    taxon_ids = fetch_taxon_ids()

    # First, fetch records with a homolog ID that possesses a C. elegans gene.
    elegans_set = dict([[int(x[0]), x[3]] for x in response_csv if x[1] == '6239'])

    for line in response_csv:
        tax_id = int(line[1])
        homolog_id = int(line[0])
        if homolog_id in elegans_set.keys() and tax_id != 6239:
            # Try to resolve the wormbase WB ID if possible.
            gene_name = elegans_set[homolog_id]
            gene_id = wormbase_gene_summary_m.resolve_gene_id(gene_name) or line[2]
            yield {'gene_id': gene_id,
                   'gene_name': gene_name,
                   'homolog_species': taxon_ids[tax_id],
                   'homolog_taxon_id': tax_id,
                   'homolog_gene': line[3],
                   'homolog_source': "Homologene",
                   'is_ortholog': False}
