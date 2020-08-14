from flask import request
from base.models import Homologs, WormbaseGeneSummary
from base.utils.decorators import jsonify_request
from sqlalchemy import or_, func
from base.views.api.api_variant import variant_query
from logzero import logger

from flask import Blueprint

api_gene_bp = Blueprint('api_gene',
                     __name__,
                     template_folder='api')


@api_gene_bp.route('/gene/homolog/<string:query>')
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
    results = Homologs.query.filter(func.lower(Homologs.homolog_gene)==query) \
                              .limit(10) \
                              .all()
    results = [x.unnest() for x in results]
    return results


@api_gene_bp.route('/gene/lookup/<string:query>')
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
    result = WormbaseGeneSummary.query.filter(or_(WormbaseGeneSummary.locus == query,
                                                  WormbaseGeneSummary.sequence_name == query,
                                                  WormbaseGeneSummary.gene_id == query)) \
                                           .first()
    if not result:
        result = WormbaseGeneSummary.query.filter(or_(WormbaseGeneSummary.locus.startswith(query),
                                                          WormbaseGeneSummary.sequence_name.startswith(query),
                                                          WormbaseGeneSummary.gene_id.startswith(query))) \
                                               .first()
    return result


@api_gene_bp.route('/gene/search/<string:query>')
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
    results = WormbaseGeneSummary.query.filter(or_(WormbaseGeneSummary.locus.startswith(query),
                                                       WormbaseGeneSummary.sequence_name.startswith(query),
                                                       WormbaseGeneSummary.gene_id.startswith(query))) \
                                           .limit(10) \
                                           .all()
    return results


@api_gene_bp.route('/gene/browser-search/<string:query>')
@jsonify_request
def combined_search(query=""):
    """Combines homolog and gene searches
    
    Args:
        query (str): Query string

    Returns:
        results (list): List of dictionaries describing the homolog.

    """
    return query_gene(query) + query_homolog(query)



@api_gene_bp.route('/gene/variants/<string:query>')
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



@api_gene_bp.route('/browser/search/<string:gene>') # Seach for IGV Browser
@jsonify_request
def api_igv_search(gene):
    """
        API gene search for IGV
    """
    result = lookup_gene(gene)
    if result:
        return {'result': [{"chromosome": result.chrom,
                'start': result.start,
                'end': result.end}]}
    else:
        return {'error': 'not found'}