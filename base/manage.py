#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
import arrow
import gunicorn  # Do not remove this line - this is here so pipreqs imports
import pandas as pd
from click import secho
from gcloud import datastore
from base.utils.gcloud import upload_file, get_item, google_storage, get_md5
from base.utils.data_utils import zipdir
from base.application import app, db_2
from base.models2 import (metadata_m,
                          strain_m,
                          wormbase_gene_summary_m,
                          wormbase_gene_m,
                          homologs_m)
from base.db.etl_strains import fetch_andersen_strains
from base.db.etl_wormbase import (fetch_gene_gtf,
                                  fetch_gene_gff_summary,
                                  fetch_orthologs)
from base.db.etl_homologene import fetch_homologene
from base import constants
from subprocess import Popen, PIPE
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base.models2 import wormbase_gene_summary_m

# Do not remove gunicorn import
secho(f"gunicorn {gunicorn.SERVER_SOFTWARE}", fg="green")

# Mapping worker database
db_mapping_worker = create_engine('sqlite:///mapping_worker/genes.db')
wormbase_gene_summary_m.metadata.create_all(db_mapping_worker)
db_mapping_worker_session = sessionmaker(bind=db_mapping_worker)()

@app.cli.command()
def init_db():
    """Initialize the database."""
    start = arrow.utcnow()
    secho('Initializing Database', fg="green")
    if os.path.exists("base/cendr.db"):
        os.remove("base/cendr.db")
    if os.path.exists("base/mapping_worker/genes.db"):
        os.remove("base/mapping_worker/genes.db")
    db_2.create_all()

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
                    db_2.session.add(key_val)
            elif type(current_var) == list:
                key_val = metadata_m(key=var,
                                     value=str(getattr(constants, var)))
                db_2.session.add(key_val)
            elif type(current_var) == dict:
                key_val = metadata_m(key=var,
                                     value=';'.join([f"{k}:{v}" for k, v in getattr(constants, var).items()]))
            else:
                key_val = metadata_m(key=var, value=str(getattr(constants, var)))
                db_2.session.add(key_val)

    db_2.session.commit()

    ##############
    # Load Genes #
    ##############
    secho('Loading summary gene table', fg='green')
    genes = list(fetch_gene_gff_summary())
    db_2.session.bulk_insert_mappings(wormbase_gene_summary_m, genes)
    secho('Save gene table for mapping worker', fg='green')
    pd.DataFrame(genes).to_csv("mapping_worker/genes.tsv.gz", compression='gzip', index=False)
    db_mapping_worker_session.close()
    secho('Loading gene table', fg='green')
    db_2.session.bulk_insert_mappings(wormbase_gene_m, fetch_gene_gtf())
    gene_summary = db_2.session.query(wormbase_gene_m.feature,
                                      db_2.func.count(wormbase_gene_m.feature)) \
                               .group_by(wormbase_gene_m.feature) \
                               .all()
    gene_summary = '\n'.join([f"{k}: {v}" for k, v in gene_summary])
    secho(f"============\nGene Summary\n------------\n{gene_summary}\n============")

    ###############################
    # Load homologs and orthologs #
    ###############################
    secho('Loading homologs from homologene', fg='green')
    db_2.session.bulk_insert_mappings(homologs_m, fetch_homologene())
    secho('Loading orthologs from WormBase', fg='green')
    db_2.session.bulk_insert_mappings(homologs_m, fetch_orthologs())

    ################
    # Load Strains #
    ################
    secho('Loading strains...', fg='green')
    db_2.session.bulk_insert_mappings(strain_m, fetch_andersen_strains())
    db_2.session.commit()
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


@app.cli.command()
def update_credentials():
    """
        Update the credentials zip file
    """
    secho("Zipping env_config", fg='green')
    zipdir('env_config/', 'env_config.zip')
    zip_creds = get_item('credential', 'travis-ci-cred')
    secho("Encrypting credentials", fg='green')
    if os.path.exists("env_config.zip.enc"):
        os.remove("env_config.zip.enc")
    comm = ['travis',
            'encrypt-file',
            'env_config.zip',
            '--key',
            zip_creds['key'],
            '--iv',
            zip_creds['iv']]
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    secho(str(out, 'utf-8'), fg='green')
    if err:
        exit(secho(str(err, 'utf-8'), fg='red'))
    os.remove("env_config.zip")


@app.cli.command()
def decrypt_credentials():
    secho("Decrypting env_config.zip.enc", fg='green')
    zip_creds = get_item('credential', 'travis-ci-cred')
    comm = ['travis',
            'encrypt-file',
            'env_config.zip.enc',
            '--force',
            '--key',
            zip_creds['key'],
            '--iv',
            zip_creds['iv'],
            '--decrypt']
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    secho(str(out, 'utf-8'), fg='green')
    if err:
        exit(secho(str(err, 'utf-8'), fg='red'))
    secho("Unzipping env_config.zip", fg='green')
    comm = ['unzip', '-qo', 'env_config.zip']
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    secho(str(out, 'utf-8'), fg='green')
    if err:
        exit(secho(str(err, 'utf-8'), fg='red'))
    os.remove("env_config.zip")
