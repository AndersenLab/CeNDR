# -*- coding: utf-8 -*-
"""

This page is intended to store application constants that change
very infrequently (if ever).

Author: Daniel E. Cook (danielecook@gmail.com)
"""

WORMBASE_VERSION = 'WS276'

STRAIN_PHOTO_PATH = 'photos/Celegans/'
STRAIN_THUMBNAIL_PATH = 'photos/Celegans/thumbnails/'

USER_ROLES = [('user', 'User'), ('admin', 'Admin')]

class PRICES:
  DIVERGENT_SET = 160
  STRAIN_SET = 640
  STRAIN = 15
  SHIPPING = 65


SHIPPING_OPTIONS = [('UPS', 'UPS'),
                    ('FEDEX', 'FEDEX'),
                    ('Flat Rate Shipping', '${} Flat Fee'.format(PRICES.SHIPPING))]

PAYMENT_OPTIONS = [('check', 'Check'),
                   ('credit_card', 'Credit Card')]

# Maps chromosome in roman numerals to integer
CHROM_NUMERIC = {"I": 1,
                 "II": 2,
                 "III": 3,
                 "IV": 4,
                 "V": 5,
                 "X": 6,
                 "MtDNA": 7}


GOOGLE_CLOUD_BUCKET = 'elegansvariation.org'
GOOGLE_CLOUD_PROJECT_ID = 'andersen-lab'

# WI Strain Info Dataset
GOOGLE_SHEETS = {"orders": "1BCnmdJNRjQR3Bx8fMjD_IlTzmh3o7yj8ZQXTkk6tTXM",
                 "WI": "1V6YHzblaDph01sFDI8YK_fP0H7sVebHQTXypGdiQIjI"}


# Report version = The current HTML template to use for reports.
REPORT_VERSION = "v2"


class URLS:
    """
        URLs are stored here so they can be easily integrated into the database
        for provenance purposes.
    """
    #
    # BAMs are now hosted on google cloud buckets
    #
    BAM_URL_PREFIX = f"https://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/bam"

    """
       Wormbase URLs
    """
    # Gene GTF
    GENE_GTF_URL = "ftp://ftp.wormbase.org/pub/wormbase/releases/{WB}/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.{WB}.canonical_geneset.gtf.gz"
    # GENE GFF_URL
    GENE_GFF_URL = "ftp://ftp.wormbase.org/pub/wormbase/releases/{WB}/species/c_elegans/PRJNA13758/c_elegans.PRJNA13758.{WB}.annotations.gff3.gz"
    # Maps wormbase ID to locus name
    GENE_IDS_URL = "ftp://ftp.wormbase.org/pub/wormbase/species/c_elegans/annotation/geneIDs/c_elegans.PRJNA13758.current.geneIDs.txt.gz"
    # Lists C. elegans orthologs
    ORTHOLOG_URL = "ftp://ftp.wormbase.org/pub/wormbase/species/c_elegans/PRJNA13758/annotation/orthologs/c_elegans.PRJNA13758.current_development.orthologs.txt"

    #
    # Ortholog URLs
    #
    # Homologene
    HOMOLOGENE_URL = 'https://ftp.ncbi.nih.gov/pub/HomoloGene/current/homologene.data'
    # Taxon IDs
    TAXON_ID_URL = 'ftp://ftp.ncbi.nih.gov/pub/taxonomy/taxdump.tar.gz'


BIOTYPES = {
    "miRNA": "microRNA",
    "piRNA": "piwi-interacting RNA",
    "rRNA": "ribosomal RNA",
    "siRNA": "small interfering RNA",
    "snRNA": "small nuclear RNA",
    "snoRNA": "small nucleolar RNA",
    "tRNA": "transfer RNA",
    "vaultRNA": "Short non-coding RNA genes that form part of the vault ribonucleoprotein complex",
    "lncRNA": "Long non-coding RNA",
    "lincRNA": "Long interspersed ncRNA",
    "pseudogene": "non-functional gene.",
    "asRNA": "Anti-sense RNA",
    "ncRNA": "Non-coding RNA",
    "scRNA": "Small cytoplasmic RNA"
}

TABLE_COLORS = {"LOW": 'success',
                "MODERATE": 'warning',
                "HIGH": 'danger'}


DEFAULT_CLOUD_CONFIG = 'default'

REPORT_VERSIONS = ['', 'v1', 'v2']
REPORT_V1_FILE_LIST = ['methods.md']
REPORT_V2_FILE_LIST = ['alignment_report.html', 'concordance_report.html', 'gatk_report.html', 'methods.md', 'reads_mapped_by_strain.tsv', 'release_notes.md']