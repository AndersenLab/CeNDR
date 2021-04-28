import io
import re
import json
import tabix
import arrow
import requests
import numpy as np
import pandas as pd
from cyvcf2 import VCF
from flask import (Blueprint,
                   jsonify,
                   render_template,
                   request,
                   abort,
                   Response)
from flask_wtf import Form
from logzero import logger
from wtforms import IntegerField, SelectField
from wtforms.validators import Required, ValidationError
from threading import Thread

from base.constants import CHROM_NUMERIC, GOOGLE_CLOUD_BUCKET 
from base.config import config
from base.models import ip_calc_ds
from base.utils.gcloud import add_task, check_blob, upload_file
from base.utils.data_utils import hash_it, unique_id
from base.utils.jwt_utils import jwt_required, get_jwt, get_current_user

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
# NOTE: Tabix cannot make requests over https!
SV_BED_URL = f"http://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/tools/pairwise_indel_primer/sv.20200815.bed.gz"
SV_VCF_URL = f"http://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/tools/pairwise_indel_primer/sv.20200815.vcf.gz"

SV_STRAINS = VCF(SV_VCF_URL).samples
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
        if val:
            val[0] = val[0].replace(",", "").replace(".", "")
        return super(FlexIntegerField, self).process_formdata(val)


class pairwise_indel_form(Form):
    """
        Form for mapping submission
    """
    strain_1 = SelectField('Strain 1', choices=STRAIN_CHOICES, default="N2", validators=[Required(), validate_uniq_strains])
    strain_2 = SelectField('Strain 2', choices=STRAIN_CHOICES, default="CB4856", validators=[Required()])
    chromosome = SelectField('Chromosome', choices=CHROMOSOME_CHOICES, validators=[Required()])
    start = FlexIntegerField('Start', default="2,018,824", validators=[Required(), validate_start_lt_stop])
    stop = FlexIntegerField('Stop', default="2,039,217", validators=[Required()])


@indel_primer_bp.route('/pairwise_indel_finder', methods=['GET'])
@jwt_required()
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
@jwt_required()
def pairwise_indel_finder_query():
    form = pairwise_indel_form()
    if form.validate_on_submit():
        data = form.data
        results = []
        strain_cmp = [data["strain_1"],
                      data["strain_2"]]
        tb = tabix.open(SV_BED_URL)
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

def create_ip_task(data_hash, site, strain1, strain2, vcf_url, username):
  """
      This is designed to be run in the background on the server.
      It will run a heritability analysis on google cloud run
  """
  id = unique_id()
  ip = ip_calc_ds(id)
  ip.data_hash = data_hash
  ip.username = username
  ip.save()

  # Perform ip request
  queue = config['INDEL_PRIMER_TASK_QUEUE']
  url = config['INDEL_PRIMER_URL']
  data = { 'hash': data_hash,
           'site': site,
           'strain1': strain1,
           'strain2': strain2,
           'vcf_url': vcf_url.replace("https", "http"),
           'ds_id': id,
           'ds_kind': ip.kind }
           
  result = add_task(queue, url, data, task_name=data_hash)

  # Update report status
  ip.status = 'SCHEDULED' if result else 'FAILED'
  ip.save()


@indel_primer_bp.route('/pairwise_indel_finder/submit', methods=["POST"])
@jwt_required()
def submit_indel_primer():
    """
        This endpoint is used to submit an indel primer job.
        The endpoint request is executed as a background task to keep the job alive.
    """
    data = request.get_json()
    user = get_current_user()

    # Generate an ID for the data based on its hash
    data_hash = hash_it(data, length=32)
    data['date'] = str(arrow.utcnow())

    # Check whether analysis has previously been run and if so - skip
    result = check_blob(f"reports/indel_primer/{data_hash}/results.tsv")
    if result:
        return jsonify({'thread_name': 'done',
                        'started': True,
                        'data_hash': data_hash})

    logger.debug("Submitting Indel Primer Job")
    # Upload query information
    data_blob = f"reports/indel_primer/{data_hash}/input.json"
    upload_file(data_blob, json.dumps(data), as_string=True)
    create_ip_task(data_hash=data_hash, site=data.get('site'), strain1=data.get('strain_1'), strain2=data.get('strain_2'), vcf_url=SV_VCF_URL, username=user.name)

    return jsonify({ 'started': True,
                    'data_hash': data_hash })


@indel_primer_bp.route("/indel_primer/result/<data_hash>")
@indel_primer_bp.route("/indel_primer/result/<data_hash>/tsv/<filename>")
@jwt_required()
def pairwise_indel_query_results(data_hash, filename = None):
    title = "Indel Primer Results"
    data = check_blob(f"reports/indel_primer/{data_hash}/input.json")
    result = check_blob(f"reports/indel_primer/{data_hash}/results.tsv")
    ready = False

    if data is None:
        return abort(404, description="Indel primer report not found")
    data = json.loads(data.download_as_string().decode('utf-8'))
    logger.info(data)
    # Get trait and set title
    title = f"Indel Primer Results {data['site']}"
    subtitle = f"{data['strain_1']} | {data['strain_2']}"

    # Set indel information
    size = data['size']
    chrom, indel_start, indel_stop = re.split(":|-", data['site'])
    indel_start, indel_stop = int(indel_start), int(indel_stop)

    if result:
        result = result.download_as_string().decode('utf-8')
        result = pd.read_csv(io.StringIO(result), sep="\t")

        # Check for no results
        empty = True if len(result) == 0 else False
        ready = True
        if empty is False:
            # left primer
            result['left_primer_start'] = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[0]).astype(int)
            result['left_primer_stop'] = result.apply(lambda x: len(x['primer_left']) + x['left_primer_start'], axis=1)

            # right primer
            result['right_primer_stop'] = result.amplicon_region.apply(lambda x: x.split(":")[1].split("-")[1]).astype(int)
            result['right_primer_start'] = result.apply(lambda x:  x['right_primer_stop'] - len(x['primer_right']), axis=1)

            # Output left and right melting temperatures.
            result[["left_melting_temp", "right_melting_temp"]] = result["melting_temperature"].str.split(",", expand = True)

            # REF Strain and ALT Strain
            ref_strain = result['0/0'].unique()[0]
            alt_strain = result['1/1'].unique()[0]

            # Extract chromosome and amplicon start/stop
            result[[None, "amp_start", "amp_stop"]] = result.amplicon_region.str.split(pat=":|-", expand=True)

            # Convert types
            result.amp_start = result.amp_start.astype(int)
            result.amp_stop = result.amp_stop.astype(int)

            result["N"] = np.arange(len(result)) + 1
            # Setup output table
            format_table = result[["N",
                                "CHROM",
                                "primer_left",
                                "left_primer_start",
                                "left_primer_stop",
                                "left_melting_temp",
                                "primer_right",
                                "right_primer_start",
                                "right_primer_stop",
                                "right_melting_temp",
                                "REF_product_size",
                                "ALT_product_size"]]

            # Format table column names
            COLUMN_NAMES = ["Primer Set",
                            "Chrom",
                            "Left Primer (LP)",
                            "LP Start",
                            "LP Stop",
                            "LP Melting Temp",
                            "Right Primer (RP)",
                            "RP Start",
                            "RP Stop",
                            "RP Melting Temp",
                            f"{ref_strain} (REF) amplicon size",
                            f"{alt_strain} (ALT) amplicon size"]

            format_table.columns = COLUMN_NAMES

            records = result.to_dict('records')

    if request.path.endswith("tsv"):
        # Return TSV of results
        return Response(format_table.to_csv(sep="\t"), mimetype="text/tab-separated-values")

    return render_template("tools/indel_primer_results.html", **locals())


