import os

import arrow

from logzero import logger
from base import constants
from base.models import (db,
                         Homologs,
                         Metadata,
                         WormbaseGene,
                         WormbaseGeneSummary)
from base.config import (CENDR_VERSION,
                         APP_CONFIG,
                         DATASET_RELEASE,
                         RELEASES)
# ETL Pipelines - fetch and format data for
# input into the sqlite database
from .etl_homologene import fetch_homologene
from .etl_strains import fetch_andersen_strains
from .etl_wormbase import (fetch_gene_gff_summary,
                           fetch_gene_gtf,
                           fetch_orthologs)


def initialize_sqlite_database(wormbase_version, db=db):
    """Create a static sqlite database
    Args:
         wormbase_version - e.g. WS245

    Generate an sqlite database
    """
    start = arrow.utcnow()
    logger.info('Initializing Database')
    SQLITE_PATH = f"base/cendr.{wormbase_version}.db"
    if os.path.exists(SQLITE_PATH):
        os.remove(SQLITE_PATH)

    from base.application import create_app
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///cendr.{wormbase_version}.db"
    app.app_context().push()
    
    db.create_all(app=app)
    db.session.commit()
 
    logger.info(f"Created {SQLITE_PATH}")

    ################
    # Set metadata #
    ################
    logger.info('Inserting metadata')
    today = arrow.utcnow().date().isoformat()
    metadata = {}
    metadata.update(vars(constants))
    metadata.update({"CENDR_VERSION": CENDR_VERSION,
                     "APP_CONFIG": APP_CONFIG,
                     "DATASET_RELEASE": DATASET_RELEASE,
                     "WORMBASE_VERSION": wormbase_version,
                     "RELEASES": RELEASES,
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
    logger.info('Loading summary gene table')
    genes = list(fetch_gene_gff_summary())
    db.session.bulk_insert_mappings(WormbaseGeneSummary, genes)
    logger.info('Save gene table for mapping worker')
    pd.DataFrame(genes).to_csv("mapping_worker/genes.tsv.gz", compression='gzip', index=False)
    db_mapping_worker_session.close()
    logger.info('Loading gene table')
    db.session.bulk_insert_mappings(WormbaseGene, fetch_gene_gtf())
    gene_summary = db.session.query(WormbaseGene.feature,
                                      db.func.count(WormbaseGene.feature)) \
                               .group_by(WormbaseGene.feature) \
                               .all()
    gene_summary = '\n'.join([f"{k}: {v}" for k, v in gene_summary])
    logger.info(f"============\nGene Summary\n------------\n{gene_summary}\n============")

    ###############################
    # Load homologs and orthologs #
    ###############################
    logger.info('Loading homologs from homologene')
    db.session.bulk_insert_mappings(Homologs, fetch_homologene())
    logger.info('Loading orthologs from WormBase')
    db.session.bulk_insert_mappings(Homologs, fetch_orthologs())

    ################
    # Load Strains #
    ################
    logger.info('Loading strains...')
    db.session.bulk_insert_mappings(Strain, fetch_andersen_strains())
    db.session.commit()
    logger.info(f"Inserted {Strain.query.count()} strains", fg="blue")

    #############
    # Upload DB #
    #############

    # Generate an md5sum of the database that can be compared with
    # what is already on google storage.
    local_md5_hash = get_md5("base/cendr.db")
    logger.info(f"Database md5 (base64) hash: {local_md5_hash}")
    gs = google_storage()
    cendr_bucket = gs.get_bucket("elegansvariation.org")
    db_releases = list(cendr_bucket.list_blobs(prefix='db/'))[1:]
    for db in db_releases:
        if db.md5_hash == local_md5_hash:
            logger.info("An identical database already exists")
            raise Exception(f"{db.name} has an identical md5sum as the database generated. Skipping upload")

    # Upload the file using todays date for archiving purposes
    logger.info('Uploading Database')
    blob = upload_file(f"db/{today}.db", "base/cendr.db")

    # Copy the database to _latest.db
    cendr_bucket.copy_blob(blob, cendr_bucket, "db/_latest.db")

    diff = int((arrow.utcnow() - start).total_seconds())
    logger.info(f"{diff} seconds")
