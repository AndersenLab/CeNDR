import os
import arrow
from click import secho
from base.models import db
from base import constants
from base.models import metadata_m

# ETL Pipelines - fetch and format data for
# input into the sqlite database
from .etl_strains import fetch_andersen_strains
from .etl_wormbase import (fetch_gene_gtf,
                           fetch_gene_gff_summary,
                           fetch_orthologs)
from .etl_homologene import fetch_homologene


def initialize_sqlite_database(wormbase_version):
    """Create a static sqlite database
    Args:
         wormbase_version - e.g. WS245

    Generate an sqlite database
    """
    start = arrow.utcnow()
    secho('Initializing Database', fg="green")
    if os.path.exists(constants.SQLITE_PATH):
        os.remove(constants.SQLITE_PATH)
    
    db.create_all()

    secho('Created cendr.db', fg="green")

    ################
    # Set metadata #
    ################
    secho('Inserting metadata', fg="green")
    today = arrow.utcnow().date().isoformat()
    for var in vars(constants):
        if not var.startswith("_"):
            # For nested constants:
            current_var = getattr(constants, var)
            if type(current_var) == type:
                for name in [x for x in vars(current_var) if not x.startswith("_")]:
                    key_val = metadata_m(key="{}/{}".format(var, name),
                                         value=getattr(current_var, name))
                    db.session.add(key_val)
            elif type(current_var) == list:
                key_val = metadata_m(key=var,
                                     value=str(getattr(constants, var)))
                db.session.add(key_val)
            elif type(current_var) == dict:
                key_val = metadata_m(key=var,
                                     value=';'.join([f"{k}:{v}" for k, v in getattr(constants, var).items()]))
            else:
                key_val = metadata_m(key=var, value=str(getattr(constants, var)))
                db.session.add(key_val)

    db.session.commit()

    ##############
    # Load Genes #
    ##############
    secho('Loading summary gene table', fg='green')
    genes = list(fetch_gene_gff_summary())
    db.session.bulk_insert_mappings(wormbase_gene_summary_m, genes)
    secho('Save gene table for mapping worker', fg='green')
    pd.DataFrame(genes).to_csv("mapping_worker/genes.tsv.gz", compression='gzip', index=False)
    db_mapping_worker_session.close()
    secho('Loading gene table', fg='green')
    db.session.bulk_insert_mappings(wormbase_gene_m, fetch_gene_gtf())
    gene_summary = db.session.query(wormbase_gene_m.feature,
                                      db.func.count(wormbase_gene_m.feature)) \
                               .group_by(wormbase_gene_m.feature) \
                               .all()
    gene_summary = '\n'.join([f"{k}: {v}" for k, v in gene_summary])
    secho(f"============\nGene Summary\n------------\n{gene_summary}\n============")

    ###############################
    # Load homologs and orthologs #
    ###############################
    secho('Loading homologs from homologene', fg='green')
    db.session.bulk_insert_mappings(homologs_m, fetch_homologene())
    secho('Loading orthologs from WormBase', fg='green')
    db.session.bulk_insert_mappings(homologs_m, fetch_orthologs())

    ################
    # Load Strains #
    ################
    secho('Loading strains...', fg='green')
    db.session.bulk_insert_mappings(strain_m, fetch_andersen_strains())
    db.session.commit()
    secho(f"Inserted {strain_m.query.count()} strains", fg="blue")

    #############
    # Upload DB #
    #############

    # Generate an md5sum of the database that can be compared with
    # what is already on google storage.
    local_md5_hash = get_md5("base/cendr.db")
    secho(f"Database md5 (base64) hash: {local_md5_hash}")
    gs = google_storage()
    cendr_bucket = gs.get_bucket("elegansvariation.org")
    db_releases = list(cendr_bucket.list_blobs(prefix='db/'))[1:]
    for db in db_releases:
        if db.md5_hash == local_md5_hash:
            secho("An identical database already exists")
            raise Exception(f"{db.name} has an identical md5sum as the database generated. Skipping upload")

    # Upload the file using todays date for archiving purposes
    secho('Uploading Database', fg='green')
    blob = upload_file(f"db/{today}.db", "base/cendr.db")

    # Copy the database to _latest.db
    cendr_bucket.copy_blob(blob, cendr_bucket, "db/_latest.db")

    diff = int((arrow.utcnow() - start).total_seconds())
    secho(f"{diff} seconds")