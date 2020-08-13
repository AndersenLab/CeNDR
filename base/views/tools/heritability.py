import os
import json
import requests
import pandas as pd
import statistics as st
from numpy import percentile 

from flask import (request,
                   jsonify,
                   render_template,
                   Blueprint,
                   redirect,
                   url_for,
                   Response)
from logzero import logger
from base.utils.data_utils import hash_it
from datetime import datetime
from threading import Thread

from base.utils.gcloud import check_blob

from base.config import config
from flask import (request,
                   jsonify,
                   render_template,
                   Blueprint,
                   redirect,
                   url_for,
                   Response,
                   Blueprint)

# ================== #
#   heritability     #
# ================== #

# Tools blueprint
heritability_bp = Blueprint('heritability',
                            __name__,
                            template_folder='tools')


@heritability_bp.route('/heritability')
def heritability():
    VARS = {"title": "Heritability Calculator"}
    return render_template('tools/heritability_calculator.html', **VARS)


def h2_task(data, data_hash):
    """
        This is designed to be run in the background on the server.
    """
    # Perform h2 request
    result = requests.post(config['HERITABILITY_URL'], data={'data': data,
                                                             'hash': data_hash})
    logger.debug(result)


@heritability_bp.route('/heritability/submit', methods=["POST"])
def submit_h2():
    """
        This endpoint is used to submit a heritability job.
        The endpoint request is executed as a background task to keep the job alive.
    """
    data = request.get_json()
    data = [x for x in data[1:] if x[0] is not None]
    header = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
    data = pd.DataFrame(data, columns=header)
    data = data.to_csv(index=False, sep="\t")
    
    # Generate an ID for the data based on its hash
    data_hash = hash_it(data, length=32)
    logger.info(data_hash)

    thread = Thread(target=h2_task, args=(data, data_hash,))
    thread.daemon = True
    thread.start()
    return jsonify({'thread_name': str(thread.name),
                    'started': True,
                    'data_hash': data_hash})


@heritability_bp.route('/heritability', methods=["POST"])
def check_data():
    data = []
    res = {}
    if request.method == "POST" or request.method == "GET":

        data = request.get_json()
        data = [x for x in data[1:] if x[0] is not None]
        header = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
        data = pd.DataFrame(data, columns=header)

        # filter missing
        data = data[data.Value.apply(lambda x: x not in [None, "", "NA"])]

        # Convert to list
        data = data.Value.astype(float).tolist()

        res = {}
        res["variance"] = "{:.2f}".format(st.variance(data))
        res["sd"] = "{:.2f}".format(st.stdev(data))
        res["minimum"] = "{:.2f}".format(min(data))
        res["maximum"] = "{:.2f}".format(max(data))
        # Calculate quartiles
        All_quartiles = percentile(data, [25, 50, 75])
        res["25"] = "{:.2f}".format(All_quartiles[0])
        res["50"] = "{:.2f}".format(All_quartiles[1])
        res["75"] = "{:.2f}".format(All_quartiles[2])
    return res


@heritability_bp.route("/heritability/h2/<data_hash>")
def heritability_result(data_hash):
    title = f"H2 Results"
    data_blob = f"reports/heritability_v1/{data_hash}/data.tsv"
    result_blob = f"reports/heritability_v1/{data_hash}/result.tsv"
    
    data = check_blob(data_blob)
    data = data.download_as_string().decode('utf-8').splitlines()
    
    result = check_blob(result_blob).download_as_string().decode('utf-8')

    data = [x.split("\t") for x in data[1:]]
    trait = data[0][2]

    return render_template("tools/heritability_results.html", **locals())


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
