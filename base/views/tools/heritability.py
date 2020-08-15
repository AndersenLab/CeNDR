import io
import requests
import statistics as st

import numpy as np
import pandas as pd

from base.utils.data_utils import hash_it
from base.utils.gcloud import check_blob, upload_file
from base.config import config

from flask import (request,
                   jsonify,
                   render_template,
                   Blueprint)
from logzero import logger
from datetime import datetime
from threading import Thread

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
        It will run a heritability analysis on google cloud run
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

    # Upload data immediately.
    data_blob = f"reports/heritability/{data_hash}/data.tsv"
    upload_file(data_blob, data, as_string=True)

    thread = Thread(target=h2_task, args=(data, data_hash,))
    thread.daemon = True
    thread.start()
    return jsonify({'thread_name': str(thread.name),
                    'started': True,
                    'data_hash': data_hash})


@heritability_bp.route('/heritability', methods=["POST"])
def check_data():
    """
        This check is used to report on the:

        Minimum
        Maximum
        Quartiles: 25, 50, 75
        Variance

        using an AJAX request - it appears at the bottom
        before the user submits.
    """
    data = request.get_json()
    data = [x for x in data[1:] if x[0] is not None]
    header = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
    data = pd.DataFrame(data, columns=header)

    # filter missing
    data = data[data.Value.apply(lambda x: x not in [None, "", "NA"])]

    # Convert to list
    data = data.Value.astype(float).tolist()

    result = {}
    result["variance"] = "{:.2f}".format(st.variance(data))
    result["sd"] = "{:.2f}".format(st.stdev(data))
    result["minimum"] = "{:.2f}".format(min(data))
    result["maximum"] = "{:.2f}".format(max(data))
    # Calculate quartiles
    All_quartiles = np.percentile(data, [25, 50, 75])
    result["25"] = "{:.2f}".format(All_quartiles[0])
    result["50"] = "{:.2f}".format(All_quartiles[1])
    result["75"] = "{:.2f}".format(All_quartiles[2])
    return result


@heritability_bp.route("/heritability/h2/<data_hash>")
def heritability_result(data_hash):
    title = f"Heritability Results"
    data = check_blob(f"reports/heritability/{data_hash}/data.tsv")
    result = check_blob(f"reports/heritability/{data_hash}/result.tsv")
    ready = False

    data = data.download_as_string().decode('utf-8')
    data = pd.read_csv(io.StringIO(data), sep="\t")
    data['AssayNumber'] = data['AssayNumber'].astype(str)
    data['label'] = data.apply(lambda x: f"{x['AssayNumber']}: {x['Value']}", 1)
    data = data.to_dict('records')
    trait = data[0]['TraitName']
    # Get trait and set title
    title = f"Heritability Results: {trait}"

    if result:
        result = result.download_as_string().decode('utf-8')
        result = pd.read_csv(io.StringIO(result), sep="\t")
        result = result.to_dict('records')[0]

        fnam=datetime.today().strftime('%Y%m%d.')+trait
        ready = True

    return render_template("tools/heritability_results.html", **locals())
