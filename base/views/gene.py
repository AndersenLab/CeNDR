from base.views.api.api_gene import lookup_gene, gene_variants
from collections import OrderedDict
from flask import render_template, Blueprint, redirect, url_for
from base.constants import BIOTYPES, TABLE_COLORS

#
# Gene View
#
gene_bp = Blueprint('gene',
                    __name__,
                    template_folder='gene')

@gene_bp.route('/')
@gene_bp.route('/<gene_name>/')
def gene(gene_name=""):
    if not gene_name:
        redirect(url_for('gene.gene', gene_name='pot-2'))

    gene_record = lookup_gene(gene_name)
    if gene_record is None:
        return render_template('errors/404.html'), 404

    # Gene Variants
    variants = gene_variants(gene_record.gene_id)

    VARS = {'title': gene_record.gene_symbol,
            'gene_record': gene_record,
            'variants': variants,
            'TABLE_COLORS': TABLE_COLORS}
    return render_template('gene/gene.html', **VARS)

