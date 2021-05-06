#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
import gunicorn  # Do not remove this line - this is here so pipreqs imports
import click
from click import secho
from base.utils.gcloud import get_item
from base.utils.data_utils import zipdir
from base.database import (initialize_sqlite_database,
                           download_sqlite_database)
from base import constants
from subprocess import Popen, PIPE

# Do not remove gunicorn import
secho(f"gunicorn {gunicorn.SERVER_SOFTWARE}", fg="green")

@click.command(help="Initialize the database")
@click.argument("wormbase_version", default=constants.WORMBASE_VERSION)
def initdb(wormbase_version=constants.WORMBASE_VERSION):
    initialize_sqlite_database(wormbase_version)


@click.command(help="Updates the strain table of the database")
@click.argument("wormbase_version", default=constants.WORMBASE_VERSION)
def update_strains(wormbase_version):
    initialize_sqlite_database(wormbase_version, strain_only=True)


@click.command(help="Download the database (used in docker container)")
def download_db():
    # Downloads the latest SQLITE database
    download_sqlite_database()


@click.command(help="Update credentials")
def update_credentials():
    """
        Update the credentials zip file
    """
    from base.application import create_app
    app = create_app()
    app.app_context().push()
    
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


@click.command(help="Decrypt credentials")
def decrypt_credentials():
    from base.application import create_app
    app = create_app()
    app.app_context().push()
    
    click.secho("Decrypting env_config.zip.enc", fg='green')
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
    click.secho(str(out, 'utf-8'), fg='green')
    if err:
        exit(secho(str(err, 'utf-8'), fg='red'))
    click.secho("Unzipping env_config.zip", fg='green')
    comm = ['unzip', '-qo', 'env_config.zip']
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    click.secho(str(out, 'utf-8'), fg='green')
    if err:
        exit(secho(str(err, 'utf-8'), fg='red'))
    os.remove("env_config.zip")
