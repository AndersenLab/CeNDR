import os
import gzip
import tabix
from flask import request, jsonify, render_template, Blueprint, redirect, url_for
from base.views.api.api_strain import get_strains
from base.constants import CHROM_NUMERIC
from logzero import logger
from collections import defaultdict

from flask_wtf import Form, RecaptchaField
from wtforms import (StringField,
                     TextAreaField,
                     IntegerField,
                     SelectField,
                     FieldList,
                     HiddenField,
                     RadioField)
from wtforms.validators import Required, Length, Email, DataRequired
from wtforms.validators import ValidationError

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

@tools_bp.route('/heritability')
def heritability_calculator():
    VARS = {"title": "Heritability Calculator"}
    return render_template('tools/heritability_calculator.html', **VARS)


#===========================#
#   pairwise_indel_finder   #
#===========================#

MIN_SV_SIZE = 50
MAX_SV_SIZE = 500

# Initial load of strain list from sv_data
# This is run when the server is started.
sv_strains = open("base/static/data/pairwise_indel_finder/sv_strains.txt", 'r').read().splitlines()
SV_COLUMNS = ["CHROM",
              "START",
              "END",
              "SUPPORT",
              "SVTYPE",
              "STRAND",	
              "SV_TYPE_CALLER",	
              "SV_POS_CALLER",	
              "STRAIN",	
              "CALLER",	
              "GT",	
              "SNPEFF_TYPE",	
              "SNPEFF_PRED",	
              "SNPEFF_EFF",	
              "SVTYPE_CLEAN",
              "TRANSCRIPT",
              "SIZE",
              "HIGH_EFF",
              "WBGeneID"]
STRAIN_CHOICES = [(x,x) for x in sv_strains]
CHROMOSOME_CHOICES = [(x,x) for x in CHROM_NUMERIC.keys()]
COLUMNS = ["CHROM", "START", "STOP", "?", "TYPE", "STRAND", ""]

def validate_uniq_strains(form, field):
    strain_1 = form.strain_1.data
    strain_2 = form.strain_2.data
    if strain_1 == strain_2:
        raise ValidationError(f"Strain 1 ({strain_1}) and Strain 2 ({strain_2}) must be different.")


def validate_start_lt_stop(form, field):
    start = form.start.data
    stop = form.stop.data
    if start >= stop:
        raise ValidationError(f"Start ({start:,}) must be less than stop ({stop:,})")

class FlexIntegerField(IntegerField):

    def process_formdata(self, val):
        logger.debug(val)
        if val:
            val[0] = val[0].replace(",", "").replace(".", "")
        logger.debug(val)
        return super(FlexIntegerField, self).process_formdata(val)

class pairwise_indel_form(Form):
    """
        Form for mapping submission
    """
    strain_1 = SelectField('Strain 1', choices=STRAIN_CHOICES, default="N2", validators=[Required(), validate_uniq_strains])
    strain_2 = SelectField('Strain 2', choices=STRAIN_CHOICES, default="CB4856", validators=[Required()])
    chromosome = SelectField('Chromosome', choices=CHROMOSOME_CHOICES, validators=[Required()])
    start = FlexIntegerField('Start', validators=[Required(), validate_start_lt_stop])
    stop = FlexIntegerField('Stop', validators=[Required()])


@tools_bp.route('/pairwise_indel_finder', methods=['GET'])
def pairwise_indel_finder():
    form = pairwise_indel_form(request.form)
    VARS = {"title": "Pairwise Indel Finder",
            "strains": sv_strains,
            "chroms": CHROM_NUMERIC.keys(),
            "form": form}
    return render_template('tools/pairwise_indel_finder.html', **VARS)

def overlaps(s1, e1, s2, e2):
    return s1 <= s2 <= e1 or s2 <= e1 <= e2

@tools_bp.route("/pairwise_indel_finder/query_indels", methods=["POST"])
def pairwise_indel_finder_query():
    form = pairwise_indel_form()
    if form.validate_on_submit():
        data = form.data
        logger.debug(form.data)
        results = []
        strain_cmp = [data["strain_1"],
                      data["strain_2"]]
        tb = tabix.open("base/static/data/pairwise_indel_finder/sv_data.bed.gz")
        logger.debug(data)
        query = tb.query(data["chromosome"], data["start"], data["stop"])
        results = []
        for row in query:
            row = dict(zip(SV_COLUMNS, row))
            if row["STRAIN"] in strain_cmp and \
                MIN_SV_SIZE <= int(row["SIZE"]) <= MAX_SV_SIZE:
                results.append(row)
        
        # mark overlaps
        first = results[0]
        for row in results[1:]:
            row["overlap"] = overlaps(first["START"], first["END"], row["START"], row["END"])
            first = row
            
        logger.debug(results)

        return jsonify(results = results)
    return jsonify({"errors": form.errors})