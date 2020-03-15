from base.views.api.api_gene import lookup_gene, gene_variants
from collections import OrderedDict
from flask import render_template, Blueprint, redirect, url_for
from base.constants import BIOTYPES, TABLE_COLORS

#
# Gene View
#
tools_bp = Blueprint('tools',
                     __name__,
                     template_folder='tools')

@tools_bp.route('/')
def tools():
    VARS = {"title": "Tools"}
    return render_template('tools/tools.html', **VARS)

@tools_bp.route('/indel')
def pairwise_indel_finder():
    VARS = {"title": "Pairwise Indel Finder"}
    return render_template('tools/pairwise_indel_finder.html', **VARS)

@tools_bp.route('/heritability')
def heritability_calculator():
    VARS = {"title": "Heritability Calculator"}
    return render_template('tools/heritability_calculator.html', **VARS)

