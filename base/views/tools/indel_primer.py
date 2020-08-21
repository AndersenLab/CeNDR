import tabix
from flask import Blueprint, jsonify, render_template, request
from flask_wtf import Form
from logzero import logger
from wtforms import IntegerField, SelectField
from wtforms.validators import Required, ValidationError

from base.constants import CHROM_NUMERIC

# Tools blueprint
indel_primer_bp = Blueprint('indel_primer',
                            __name__,
                            template_folder='tools')

# =========================== #
#    pairwise_indel_finder    #
# =========================== #

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

STRAIN_CHOICES = [(x, x) for x in sv_strains]
CHROMOSOME_CHOICES = [(x, x) for x in CHROM_NUMERIC.keys()]
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
    start = FlexIntegerField('Start', default="1,462,000", validators=[Required(), validate_start_lt_stop])
    stop = FlexIntegerField('Stop', default="1,466,000", validators=[Required()])


@indel_primer_bp.route('/pairwise_indel_finder', methods=['GET'])
def indel_primer():
    """
        Main view
    """
    form = pairwise_indel_form(request.form)
    VARS = {"title": "Pairwise Indel Finder",
            "strains": sv_strains,
            "chroms": CHROM_NUMERIC.keys(),
            "form": form}
    return render_template('tools/pairwise_indel_finder.html', **VARS)


def overlaps(s1, e1, s2, e2):
    return s1 <= s2 <= e1 or s2 <= s1 <= e2


@indel_primer_bp.route("/pairwise_indel_finder/query_indels", methods=["POST"])
def pairwise_indel_finder_query():
    form = pairwise_indel_form()
    if form.validate_on_submit():
        data = form.data
        results = []
        strain_cmp = [data["strain_1"],
                      data["strain_2"]]
        tb = tabix.open("base/static/data/pairwise_indel_finder/sv_data.bed.gz")
        query = tb.query(data["chromosome"], data["start"], data["stop"])
        results = []
        for row in query:
            row = dict(zip(SV_COLUMNS, row))
            row["START"] = int(row["START"])
            row["END"] = int(row["END"])
            if row["STRAIN"] in strain_cmp and \
                MIN_SV_SIZE <= int(row["SIZE"]) <= MAX_SV_SIZE:
                row["site"] = f"{row['CHROM']}:{row['START']}-{row['END']} ({row['SVTYPE']})"
                results.append(row)
        
        # mark overlaps
        if results:
            results[0]['overlap'] = False
            first = results[0]
            for idx, row in enumerate(results[1:]):
                row["overlap"] = overlaps(first["START"], first["END"], row["START"], row["END"])
                if row["overlap"]:
                    results[idx]['overlap'] = True
                first = row
            
            # Filter overlaps
            results = [x for x in results if x['overlap'] is False]
            sorted(results, key=lambda x: (x["START"], x["END"]))
            return jsonify(results=results)
        return jsonify(results=[])
    return jsonify({"errors": form.errors})
