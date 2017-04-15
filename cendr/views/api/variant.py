# NEW API

from cendr import api, cache, app
from cyvcf2 import VCF
from flask import jsonify
import re
import sys
from subprocess import Popen, PIPE


def get_region(region):
    m = re.match("^([0-9A-Za-z]+):([0-9]+)-([0-9]+)$", region)
    if not m:
        return msg(None, "Invalid region", 400)

    chrom = m.group(1)
    start = int(m.group(2))
    end = int(m.group(3))
    return chrom, start, end


@app.route('/api/variant/<region>')
def variant_from_region(region):
    vcf = "http://storage.googleapis.com/elegansvariation.org/releases/{version}/WI.{version}.vcf.gz".format(version = 20170312)
    m = re.match("^([0-9A-Za-z]+):([0-9]+)-([0-9]+)$", region)
    if not m:
        return "Error - malformed region.", 400
    start = int(m.group(2))
    end = int(m.group(3))

    if start >= end:
        return "Invalid start and end region values", 400
    if end - start > 1e5:
        return "Maximum region size is 100 kb", 400

    comm = ["bcftools", "view", vcf, region]
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    #if err:
    #    return err, 400
    #v = VCF(out)
    return jsonify({"out": out.splitlines(), "comm": ' '.join(comm)})
