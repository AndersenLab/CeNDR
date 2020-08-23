import tabix
import arrow
import requests
from flask import Blueprint, jsonify, render_template, request
from flask_wtf import Form
from logzero import logger
from wtforms import IntegerField, SelectField
from wtforms.validators import Required, ValidationError

from base.utils.gcloud import check_blob, upload_file
from base.utils.data_utils import hash_it
from base.constants import CHROM_NUMERIC
from threading import Thread

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
SV_STRAINS = requests.get("https://storage.googleapis.com/elegansvariation.org/tools/pairwise_indel_primer/sv_strains.txt").text.splitlines()
SV_DATA_URL = "http://storage.googleapis.com/elegansvariation.org/tools/pairwise_indel_primer/WI.HARD_FILTERED.FP.bed.gz"
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

STRAIN_CHOICES = [(x, x) for x in SV_STRAINS]
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
            "strains": SV_STRAINS,
            "chroms": CHROM_NUMERIC.keys(),
            "form": form}
    return render_template('tools/indel_primer.html', **VARS)


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
        tb = tabix.open(SV_DATA_URL)
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


def indel_primer_task(data, data_hash):
    """
        This is designed to be run in the background on the server.
        It will run a heritability analysis on google cloud run
    """
    # Perform h2 request
    #result = requests.post(config['HERITABILITY_URL'], data={'data': data,
    #                                                         'hash': data_hash})
    logger.debug(data)


@indel_primer_bp.route('/pairwise_indel_finder/submit', methods=["POST"])
def submit_indel_primer():
    """
        This endpoint is used to submit a heritability job.
        The endpoint request is executed as a background task to keep the job alive.
    """
    data = request.get_json()
    data['date'] = str(arrow.utcnow())

    # Generate an ID for the data based on its hash
    data_hash = hash_it(data, length=32)
    logger.debug(data_hash)

    # Upload query information
    data_blob = f"reports/indel_primer/{data_hash}/data.json"
    upload_file(data_blob, str(data), as_string=True)

    thread = Thread(target=indel_primer_task, args=(data, data_hash,))
    thread.daemon = True
    thread.start()
    return jsonify({'thread_name': str(thread.name),
                    'started': True,
                    'data_hash': data_hash})


def pairwise_indel_query_results():
    return render_template("tools/indel_primer_results.html")