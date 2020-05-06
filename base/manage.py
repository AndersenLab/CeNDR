#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
import gunicorn  # Do not remove this line - this is here so pipreqs imports
import click
from base.utils.gcloud import upload_file, get_item, google_storage, get_md5
from base.utils.data_utils import zipdir
from base.database import initialize_sqlite_database
from base.models import (metadata_m,
                         strain_m,
                         wormbase_gene_summary_m,
                         wormbase_gene_m,
                         homologs_m)
from base import constants
from subprocess import Popen, PIPE
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Do not remove gunicorn import
click.secho(f"gunicorn {gunicorn.SERVER_SOFTWARE}", fg="green")

# Mapping worker database
db_mapping_worker = create_engine('sqlite:///mapping_worker/genes.db')
wormbase_gene_summary_m.metadata.create_all(db_mapping_worker)
db_mapping_worker_session = sessionmaker(bind=db_mapping_worker)()



@click.argument("wormbase_version")
def init_db(wormbase_version=constants.WORMBASE_VERSION):
    initialize_sqlite_database(wormbase_version)


def update_credentials():
    """
        Update the credentials zip file
    """
    click.secho("Zipping env_config", fg='green')
    zipdir('env_config/', 'env_config.zip')
    zip_creds = get_item('credential', 'travis-ci-cred')
    click.secho("Encrypting credentials", fg='green')
    if os.path.exists("env_config.zip.enc"):
        os.remove("env_config.zip.enc")
    comm = ['travis',
            'encrypt-file',
            'env_config.zip',
            "--org",
            '--key',
            zip_creds['key'],
            '--iv',
            zip_creds['iv']]
    print(' '.join(comm))
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    secho(str(out, 'utf-8'), fg='green')
    if err:
        exit(secho(str(err, 'utf-8'), fg='red'))
    os.remove("env_config.zip")


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
