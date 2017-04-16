# NEW API

from cendr import api, cache, app
from cyvcf2 import VCF
from flask import jsonify
import re
import sys
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE


def get_region(region):
    m = re.match("^([0-9A-Za-z]+):([0-9]+)-([0-9]+)$", region)
    if not m:
        return "Invalid region", 400

    chrom = m.group(1)
    start = int(m.group(2))
    end = int(m.group(3))
    return chrom, start, end


@app.route('/api/variant/<region>')
def variant_from_region(region):
    vcf = "http://storage.googleapis.com/elegansvariation.org/releases/{version}/WI.{version}.vcf.gz".format(version = 20170312)
    chrom, start, end = get_region(region)

    if start >= end:
        return "Invalid start and end region values", 400
    if end - start > 1e5:
        return "You can only query a maximum of 100 kb", 400

    comm = ["bcftools", "view", vcf, region]
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    tfile = NamedTemporaryFile()
    json_out = []
    with tfile as f:
        f.write(out)
        v = VCF(tfile.name)
        for record in v:
            json_out.append({
                "CHROM": record.CHROM,
                "POS": record.POS,
                "REF": record.REF,
                "ALT": record.ALT,
                "GT": dict(zip(v.samples, record.gt_bases)),
                "INFO": dict(record.INFO)
                })
    return jsonify({"out": json_out, "comm": ' '.join(comm)})
