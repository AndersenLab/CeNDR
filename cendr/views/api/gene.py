from cendr import app
from cendr.models import wb_gene
from flask import jsonify

def get_gene_region(gene):
    result = list(wb_gene.filter((wb_gene.Name == gene) |
                                 (wb_gene.sequence_name == gene) |
                                 (wb_gene.locus == gene))
                         .dicts()
                         .execute())
    del result[0]['id']
    if len(result) == 1:
        return result[0]
    else:
        return None

@app.route('/api/gene/<string:gene>')
def api_get_gene_region(gene):
    return jsonify(get_gene_region(gene))