from flask import request
from base.models import strain
from base.models2 import homologs_m, wormbase_gene_summary_m
from base.application import app, db_2
from base.utils.decorators import jsonify_request
from sqlalchemy import or_, func


@app.route('/api/gene/homolog/<string:query>')
@jsonify_request
def query_homolog(query=""):
    """Query homolog

    Query the homologs database and return C. elegans homologs.

    Args:
        query (str): Query string

    Returns:
        results (list): List of dictionaries describing the homolog.

    """
    query = request.args.get('query') or query
    query = query.lower()
    results = homologs_m.query.filter(func.lower(homologs_m.homolog_gene)==query) \
                              .limit(10) \
                              .all()
    results = [x.unnest() for x in results]
    return results


@app.route('/api/gene/lookup/<string:query>')
@jsonify_request
def lookup_gene(query=""):
    """Lookup a single gene

    Lookup gene in the wormbase summary gene table.

    Args:
        query (str): Query string

    Returns:
        result (dict): List of dictionaries describing the homolog.

    """
    query = request.args.get('query') or query
    result = wormbase_gene_summary_m.query.filter(or_(wormbase_gene_summary_m.locus.startswith(query),
                                                      wormbase_gene_summary_m.sequence_name.startswith(query),
                                                      wormbase_gene_summary_m.gene_id.startswith(query))) \
                                           .first()
    return result


@app.route('/api/gene/search/<string:query>')
@jsonify_request
def query_gene(query=""):
    """Query gene

    Query genes in the wormbase summary gene table.

    Args:
        query (str): Query string

    Returns:
        results (list): List of dictionaries with gene results.


    """
    query = request.args.get('query') or query
    results = wormbase_gene_summary_m.query.filter(or_(wormbase_gene_summary_m.locus.startswith(query),
                                                       wormbase_gene_summary_m.sequence_name.startswith(query),
                                                       wormbase_gene_summary_m.gene_id.startswith(query))) \
                                           .limit(10) \
                                           .all()
    return results


@app.route('/api/gene/browser-search/<string:query>')
@jsonify_request
def combined_search(query=""):
    """Combines homolog and gene searches
    
    Args:
        query (str): Query string

    Returns:
        results (list): List of dictionaries describing the homolog.

    """

    return query_gene(query, as_list=True) + query_homolog(query, as_list=True)


