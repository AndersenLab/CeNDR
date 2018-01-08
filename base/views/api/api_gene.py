from flask import request
from base.models import strain
from base.models2 import homologs_m, wormbase_gene_summary_m
from base.application import app
from base.utils.decorators import jsonify_request


@app.route('/api/gene/<string:query>')
#@jsonify_request
def query_homolog(query=""):
    """
        Return homologs from a query
    """
    query = request.args.get('query') or query
    results = homologs_m.query.join(wormbase_gene_summary_m) \
                                           .filter(homologs_m.homolog_gene==query) \
                                           .limit(10) \
                                           .all()
    return results

