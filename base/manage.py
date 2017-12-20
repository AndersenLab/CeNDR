import os
from click import echo, style
from base.application import app, db_2
from base.models2 import wormbase_gene_m
from base.db.etl_strains import fetch_andersen_strains
from base.db.etl_wormbase import fetch_gene_gtf


def e(echo_string, color="white"):
    return echo(style(echo_string, fg=color))


@app.cli.command()
def initdb():
    """Initialize the strain database."""
    echo(style('Initializing Database', "green"))
    if os.path.exists("base/cendr.db"):
        os.remove("base/cendr.db")
    db_2.create_all()

    echo(style('Created cendr.db', "green"))

    ##############
    # Load Genes #
    ##############
    e('Loading genes...', 'white')
    db_2.session.bulk_insert_mappings(wormbase_gene_m, fetch_gene_gtf())
    gene_summary = db_2.session.query(wormbase_gene_m.feature,
                                      db_2.func.count(wormbase_gene_m.feature)) \
                               .group_by(wormbase_gene_m.feature) \
                               .all()
    gene_summary = '\n'.join([f"{k}: {v}" for k, v in gene_summary])
    e(f"============\nGene Summary\n------------\n{gene_summary}\n============")
    
    ################
    # Load Strains #
    ################
    e('Loading strains...', 'white')
    db_2.session.bulk_insert_mappings(db_2.strain_m, fetch_andersen_strains())
    db_2.session.commit()
    e(f"Inserted {db_2.strain_m.query.count()} strains", "blue")