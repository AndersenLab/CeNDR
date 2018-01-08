# -*- coding: utf-8 -*-
"""

Fetches the homologene database

Author: Daniel E. Cook (danielecook@gmail.com)
"""
import re
import tarfile
import csv
import requests
from base.db.etl_wormbase import get_gene_ids
from urllib.request import urlretrieve, urlopen
from tempfile import NamedTemporaryFile
from base.models2 import wormbase_gene_summary_m


# Homologene database
HOMOLOGENE_URL = 'https://ftp.ncbi.nih.gov/pub/HomoloGene/current/homologene.data'
TAXON_ID_URL = 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz'


def fetch_taxon_ids():
    """
        Downloads mapping of taxon-ids to species names.
    """
    taxon_file = NamedTemporaryFile(suffix='tar')
    out, err = urlretrieve(TAXON_ID_URL, taxon_file.name)
    tar = tarfile.open(out)
    # Read names file
    names_dmp = tar.extractfile('names.dmp')
    names_dmp = names_dmp.read().decode('utf-8').splitlines()
    lines = [re.split('\t\|[\t]?', x) for x in names_dmp]
    taxon_ids = {int(l[0]):l[1] for l in lines if l[3] == 'scientific name'}
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
    response = requests.get(HOMOLOGENE_URL)
    response_csv = list(csv.reader(response.content.decode('utf-8').splitlines(), delimiter='\t'))
    
    taxon_ids = fetch_taxon_ids()

    # In this loop we add the homologene id (line[0]) if there's a c_elegans gene
    # (line[1]) in the group.
    fields = ['homologene',
              'taxon_id',
              'gene_id',
              'gene_symbol',
              'protein_gi',
              'protein_accession',
              'species',
              'locus_name']

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

