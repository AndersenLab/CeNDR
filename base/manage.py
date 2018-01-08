import os
import arrow
from click import secho
from base.application import app, db_2
from base.models2 import strain_m, wormbase_gene_summary_m, wormbase_gene_m, homologs_m
from base.db.etl_strains import fetch_andersen_strains
from base.db.etl_wormbase import fetch_gene_gtf, fetch_gene_gff_summary, fetch_orthologs
from base.db.etl_homologene import fetch_homologene

@app.cli.command()
def initdb():
    """Initialize the database."""
    start = arrow.utcnow()
    secho('Initializing Database', fg="green")
    if os.path.exists("base/cendr.db"):
        os.remove("base/cendr.db")
    db_2.create_all()

    secho('Created cendr.db', fg="green")

    ##############
    # Load Genes #
    ##############
    secho('Loading summary gene table', fg='green')
    db_2.session.bulk_insert_mappings(wormbase_gene_summary_m, fetch_gene_gff_summary())
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
    diff = int((arrow.utcnow() - start).total_seconds())
    secho(f"{diff} seconds")