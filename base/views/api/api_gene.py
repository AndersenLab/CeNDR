from flask import request
from base.models import homologs_m, wormbase_gene_summary_m
from base.utils.decorators import jsonify_request
from sqlalchemy import or_, func
from base.views.api.api_variant import variant_query

from flask import Blueprint

api_gene_bp = Blueprint('api_gene',
                     __name__,
                     template_folder='api')


@api_gene_bp.route('/api/gene/homolog/<string:query>')
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


@api_gene_bp.route('/api/gene/lookup/<string:query>')
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
    # First identify exact match
    result = wormbase_gene_summary_m.query.filter(or_(wormbase_gene_summary_m.locus == query,
                                                  wormbase_gene_summary_m.sequence_name == query,
                                                  wormbase_gene_summary_m.gene_id == query)) \
                                           .first()
    if not result:
        result = wormbase_gene_summary_m.query.filter(or_(wormbase_gene_summary_m.locus.startswith(query),
                                                          wormbase_gene_summary_m.sequence_name.startswith(query),
                                                          wormbase_gene_summary_m.gene_id.startswith(query))) \
                                               .first()
    return result


@api_gene_bp.route('/api/gene/search/<string:query>')
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


@api_gene_bp.route('/api/gene/browser-search/<string:query>')
@jsonify_request
def combined_search(query=""):
    """Combines homolog and gene searches
    
    Args:
        query (str): Query string

    Returns:
        results (list): List of dictionaries describing the homolog.

    """
    return query_gene(query) + query_homolog(query)



@api_gene_bp.route('/api/gene/variants/<string:query>')
@jsonify_request
def gene_variants(query):
    """Return a list of variants within a gene.

    Args:
        query: gene name or ID

    Returns:
        results (list): List of variants within a gene
    """

    gene_record = lookup_gene(query)
    gene_variants = variant_query(gene_record.interval)
    #for row in gene_variants:
        # Filter ANN for annotations for gene
    #    row['ANN'] = [x for x in row['ANN'] if gene_record.gene_id == x['gene_id']]
    return gene_variants



@api_gene_bp.route('/api/browser/search/<string:gene>') # Seach for IGV Browser
@jsonify_request
def api_igv_search(gene):
    """
        API gene search for IGV
    """
    result = lookup_gene(gene)
    return {'result': [{"chromosome": result.chrom,
            "start": result.start,
            "end": result.end}]}
