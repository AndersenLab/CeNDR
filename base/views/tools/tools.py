import os
import tabix

from flask import request, jsonify, render_template, Blueprint, redirect, url_for
from base.views.api.api_strain import get_strains
from base.constants import CHROM_NUMERIC
from base.config import HERITABILITY_URL
from requests_futures.sessions import FuturesSession
from logzero import logger
from collections import defaultdict
from requests_futures.sessions import FuturesSession
from base.utils.data_utils import hash_it

import fileinput, glob
import json, re
import time, os
from datetime import datetime

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
from numpy import percentile 
import statistics as st

import pandas as pd
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


@tools_bp.route('/pairwise_indel_finder', methods=['GET'])
def pairwise_indel_finder():
    form = pairwise_indel_form(request.form)
    VARS = {"title": "Pairwise Indel Finder",
            "strains": sv_strains,
            "chroms": CHROM_NUMERIC.keys(),
            "form": form}
    return render_template('tools/pairwise_indel_finder.html', **VARS)


def overlaps(s1, e1, s2, e2):
    return s1 <= s2 <= e1 or s2 <= s1 <= e2


@tools_bp.route("/pairwise_indel_finder/query_indels", methods=["POST"])
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


# ================== #
#   heritability     #
# ================== #


@tools_bp.route('tools/heritability_calculator_res', methods=['GET', 'POST'])
def getRes():
    if request.method == "POST" or request.method == "GET":
        results = []
        ctd = []
        data = request.args.get('jbd')

        if os.path.isfile('./jobsD/'+data+'.out'): 
            for li in fileinput.input('./jobsD/'+data+'.txt'):
                if not li.startswith("AssayNumber"): results.append(li.rstrip().split(','))
                
            with open('./jobsD/'+data+'.json') as json_file:
                ctd = json.load(json_file)
            
            trait = ctd[1]['t']
            
            da = []
            for li in fileinput.input('./jobsD/'+data+'.out'):
                if not li.startswith('"H2"'): da = [str("{:.2f}".format(float(x)*100)) for x in li.rstrip().split('\t')[1:]]
            XX = da[0]
            X = da[1]
            Y = da[2]
            return(render_template('tools/heritability_calculator_res.html', res=results, cdt=json.dumps(ctd), trait=trait, XX=XX, X=X, Y=Y, fnam=datetime.today().strftime('%Y%m%d.')+trait))
    return render_template('tools/heritability_calculator_processing.html')


@tools_bp.route('/check_h2', methods=['GET', 'POST'])
def check_h2_data():
    data = []
    res = {}
    if request.method == "POST" or request.method == "GET":
        clicked=request.get_json()
        htcalData = json.loads(clicked)
        print(htcalData)
        for i in range(len(htcalData)):
            if htcalData[i][4] is not None and not (htcalData[i][4] == ""):
                if not (htcalData[i][4] == "NA"  or "Strain" in htcalData[i]):
                    data.append(float(htcalData[i][4]))
        
        res = {}
        res["variance"] = "{:.2f}".format(st.variance(data))
        res["sd"] = "{:.2f}".format(st.stdev(data))
        res["minimum"] = "{:.2f}".format(min(data))
        res["maximum"] = "{:.2f}".format(max(data)) 
        All_quartiles = percentile(data, [25, 50, 75])
        res["25% quartile"] = "{:.2f}".format(All_quartiles[0])
        res["50% quartile"] = "{:.2f}".format(All_quartiles[1])
        res["75% quartile"] = "{:.2f}".format(All_quartiles[2])
        
    return res	


@tools_bp.route("/submit_h2", methods=["POST"])
def submit_h2():
    """
        This endpoint is used to submit a heritability job.
    """
    session = FuturesSession()
    data = request.get_json()
    data = [x for x in data[1:] if x[0] is not None]
    header = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
    data = pd.DataFrame(data, columns=header)
    data = data.to_csv(index=False, sep="\t")

    # Generate an ID for the data based on its hash
    data_hash = hash_it(data, length=32)
    
    # Perform request
    result = session.post(HERITABILITY_URL, data={'data': data,
                                                  'hash': data_hash})
    return result

@tools_bp.route('/getHTdata', methods=['GET', 'POST'])
def getHTData():
    if request.method == "POST" or request.method == "GET":
        data = request.get_json()
        logger.info(data)
        htcalData = json.loads(clicked)
        ## create chartData.
        flag = 0
        if (clicked == ""): flag = 1
        clicked = ""
        chData = []

        #create url
        u = "/indexHT_res?jbd="+jbd
        trait = []
        with open("./jobsD/"+jbd+'.txt', 'w') as out:
            out.write(','.join(['AssayNumber', 'Strain', 'TraitName', 'Replicate', 'Value'])+'\n')
            for i in range(len(htcalData)):
                if htcalData[i][4] is not None and not (htcalData[i][4] == ""):
                    if not (htcalData[i][4] == "NA"  or "Strain" in htcalData[i]):
                        out.write(','.join(htcalData[i])+'\n')
                        if not htcalData[i][2] in trait: trait.append(htcalData[i][2])
                        chData.append({"a":htcalData[i][0],"s":htcalData[i][1],"v":htcalData[i][4],"t":htcalData[i][2]}) #+"_"+htcalData[i][1]+"_"+htcalData[i][3]})

        with open("./jobsD/"+jbd+'.json', 'w') as out:
            out.write(json.dumps(chData))
            
        #start execution
        if len(trait) > 1 : u = ""
        else:
            import os
            pid = os.spawnvp(os.P_NOWAIT, 'docker', ['docker', 'run', '-v', jobsDpath+'/jobsD:/home/data', 'nwuniv/htcal.v1.0', 'Rscript', '/home/script/H2_script.R', '/home/data/'+jbd+'.txt', '/home/data/'+jbd+'.out'])
        #return url
        #if pid == "": u = ""
        return(json.dumps({"url": u}))
