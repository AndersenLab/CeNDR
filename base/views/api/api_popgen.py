from flask import jsonify
from base.application import app
from subprocess import Popen, PIPE
from base.constants import DATASET_RELEASE
from logzero import logger


@app.route('/api/tajima/<string:chrom>/<int:start>/<int:end>')
def tajima(chrom, start, end):
    """
        PARAMETERS
            chrom
            start
            end

        RETURNS:
            JSON dict of x (position) and y (Tajima's scores) for
            the specified interval.
            {
                "x": [<numeric: position>],
                "y": [<numeric: Tajima's D scores>]
            }

    """
    url = "http://storage.googleapis.com/elegansvariation.org/releases/{DATASET_RELEASE}/tajima/WI.{DATASET_RELEASE}.tajima.bed.gz".format(DATASET_RELEASE=DATASET_RELEASE)
    comm = ['tabix', url, "{chrom}:{start}-{end}".format(**locals())]
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()

    if err:
        return jsonify(error=str(err, encoding='utf-8')), 404
    out = [x.split("\t") for x in str(out, encoding='ascii').splitlines()]
    data = [(int(x[2]) + 50000, float(x[5])) for x in out]
    response = {"x": [x[0] for x in data],
                "y": [x[1] for x in data]}
    return jsonify(response)
