from flask import jsonify
from cendr import app, releases, autoconvert
from subprocess import Popen, PIPE


@app.route('/api/tajima/<string:chrom>/<int:start>/<int:end>')
def tajima(chrom, start, end):
    url = "http://storage.googleapis.com/elegansvariation.org/releases/{release}/tajima/WI.{release}.tajima.bed.gz".format(release = releases[0])
    comm =['tabix', url, "{chrom}:{start}-{end}".format(**locals())]
    out, err = Popen(comm, stdout = PIPE, stderr = PIPE).communicate()
    out = [map(autoconvert, x.split("\t")) for x in out.splitlines()]
    data = [(int(x[2]) + 50000, float(x[5])) for x in out]
    response = {"x": [x[0] for x in data], "y": [x[1] for x in data]}
    return jsonify(response)
