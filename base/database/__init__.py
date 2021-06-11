import os
import arrow
import pickle
from rich.console import Console

from base import constants
from base.constants import URLS, GOOGLE_CLOUD_BUCKET
from base.config import config
from base.utils.data_utils import download
from base.utils.decorators import timeit
from base.models import (StrainAnnotatedVariants, db,
                         Strain,
                         Homologs,
                         Metadata,
                         WormbaseGene,
                         WormbaseGeneSummary)
# ETL Pipelines - fetch and format data for
# input into the postgres database
from base.database.etl_homologene import fetch_homologene
from base.database.etl_strains import fetch_andersen_strains
from base.database.etl_wormbase import (fetch_gene_gff_summary,
                                        fetch_gene_gtf,
                                        fetch_orthologs)
from base.database.etl_variant_annot import fetch_strain_variant_annotation_data

DOWNLOAD_PATH = ".download"
console = Console()

def download_fname(download_path: str, download_url: str):
  return os.path.join(download_path,
                      download_url.split("/")[-1])

@timeit
def initialize_postgres_database(sel_wormbase_version,
                               strain_only=False):
  """Create a postgres database
  Args:
        sel_wormbase_version - e.g. WS276

  Generate a postgres database
  """
  console.log("Initializing Database")
  DATASET_RELEASE = config['DATASET_RELEASE']

  # Download wormbase files
  if strain_only is False:
    f = download_external_data(sel_wormbase_version)

  from base.application import create_app
  app = create_app()
  app.app_context().push()

  app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://admin:password@localhost/cendr'

  
  if strain_only is True:
    reset_tables(app, db, tables=[Strain.__table__])
  else:
    reset_tables(app, db)

  load_strains(db)
  if strain_only is True:
    console.log('Finished loading strains')
    return

  load_metadata(db, sel_wormbase_version)
  load_genes_summary(db, f)
  load_genes_table(db, f)
  load_homologs(db, f)
  load_orthologs(db, f)
  load_variant_annotation(db, f)
  generate_gene_dict()


##########################
# Download external data #
##########################
@timeit
def download_external_data(sel_wormbase_version):
  console.log('Downloading External Data...')
  if not os.path.exists(DOWNLOAD_PATH):
      os.makedirs(DOWNLOAD_PATH)

  # Parallel URL download
  console.log("Downloading Wormbase Data")
  GENE_GFF_URL = URLS.GENE_GFF_URL.format(WB=sel_wormbase_version)
  GENE_GTF_URL = URLS.GENE_GTF_URL.format(WB=sel_wormbase_version)
  download([URLS.STRAIN_VARIANT_ANNOTATION_URL,
            GENE_GFF_URL,
            GENE_GTF_URL,
            URLS.GENE_IDS_URL,
            URLS.HOMOLOGENE_URL,
            URLS.ORTHOLOG_URL,
            URLS.TAXON_ID_URL],
            DOWNLOAD_PATH)

  fnames = {
    "sva": download_fname(DOWNLOAD_PATH,URLS.STRAIN_VARIANT_ANNOTATION_URL),
    "gff": download_fname(DOWNLOAD_PATH, GENE_GFF_URL),
    "gtf": download_fname(DOWNLOAD_PATH, GENE_GTF_URL),
    "gene_ids": download_fname(DOWNLOAD_PATH, URLS.GENE_IDS_URL),
    "homologene": download_fname(DOWNLOAD_PATH, URLS.HOMOLOGENE_URL),
    "ortholog": download_fname(DOWNLOAD_PATH, URLS.ORTHOLOG_URL)
  }
  return fnames


################
# Reset Tables #
################
@timeit
def reset_tables(app, db, tables = None):
  if tables is None:
    console.log('Dropping all tables...')
    db.drop_all(app=app)
    console.log('Creating all tables...')
    db.create_all(app=app)
  else:
    console.log(f'Dropping tables: ${tables}')
    db.metadata.drop_all(bind=db.engine, checkfirst=True, tables=tables)
    console.log(f'Creating tables: ${tables}')
    db.metadata.create_all(bind=db.engine, tables=tables)

  db.session.commit()



################
# Load Strains #
################
@timeit
def load_strains(db): 
  console.log('Loading strains...')
  andersen_strains = fetch_andersen_strains()
  db.session.bulk_insert_mappings(Strain, andersen_strains)
  db.session.commit()
  console.log(f"Inserted {Strain.query.count()} strains")


################
# Set metadata #
################
@timeit
def load_metadata(db, sel_wormbase_version):
  start = arrow.utcnow()
  console.log('Inserting metadata')
  metadata = {}
  metadata.update(vars(constants))
  metadata.update({"CENDR_VERSION": config['CENDR_VERSION'],
                    "APP_CONFIG": config['APP_CONFIG'],
                    "DATASET_RELEASE": config['DATASET_RELEASE'],
                    "WORMBASE_VERSION": sel_wormbase_version,
                    "RELEASES": config['RELEASES'],
                    "DATE": arrow.utcnow()})

  for k, v in metadata.items():
    if not k.startswith("_"):
      # For nested constants:
      if type(v) == type:
        for name in [x for x in dir(v) if not x.startswith("_")]:
          key_val = Metadata(key="{}/{}".format(k, name),
                              value=getattr(v, name))
          db.session.add(key_val)
      else:
        key_val = Metadata(key=k, value=str(v))
        db.session.add(key_val)

  db.session.commit()


##############
# Load Genes #
##############
@timeit
def load_genes_summary(db, f):
  console.log('Loading summary gene table')
  gene_summary = fetch_gene_gff_summary(f['gff'])
  db.session.bulk_insert_mappings(WormbaseGeneSummary, gene_summary)
  db.session.commit()


@timeit
def load_genes_table(db, f):
  console.log('Loading gene table')
  genes = fetch_gene_gtf(f['gtf'], f['gene_ids'])
  db.session.bulk_insert_mappings(WormbaseGene, genes)
  db.session.commit();
  
  results = db.session.query(WormbaseGene.feature, db.func.count(WormbaseGene.feature)) \
                            .group_by(WormbaseGene.feature) \
                            .all()
  result_summary = '\n'.join([f"{k}: {v}" for k, v in results])
  console.log(f"============\nGene Summary\n------------\n{result_summary}\n============\n")


###############################
#        Load homologs        #
###############################
@timeit
def load_homologs(db, f):
  console.log('Loading homologs from homologene')
  homologene = fetch_homologene(f['homologene'])
  db.session.bulk_insert_mappings(Homologs, homologene)
  db.session.commit()
  

###############################
#       Load Orthologs        #
###############################
@timeit
def load_orthologs(db, f):
  console.log('Loading orthologs from WormBase')
  orthologs = fetch_orthologs(f['ortholog'])
  db.session.bulk_insert_mappings(Homologs, orthologs)
  db.session.commit()


######################################
# Load Strain Variant Annotated Data #
######################################
@timeit
def load_variant_annotation(db, f):
  console.log('Loading strain variant annotated csv')
  sva_data = fetch_strain_variant_annotation_data(f['sva'])
  db.session.bulk_insert_mappings(StrainAnnotatedVariants, sva_data)
  db.session.commit()


# =========================== #
#   Generate gene id dict     #
# =========================== #
# Create a gene dictionary to match wormbase IDs to either the locus name
# or a sequence id
@timeit
def generate_gene_dict():
  console.log('Generating gene_dict.pkl')
  gene_dict = {x.gene_id: x.locus or x.sequence_name for x in WormbaseGeneSummary.query.all()}
  pickle.dump(gene_dict, open("base/static/data/gene_dict.pkl", 'wb'))
