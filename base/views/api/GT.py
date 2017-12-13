from flask_restful import Resource
from base import api, cache
import pickle
import base64
import zlib
from base.models import WI, strain
from base import app
from flask import jsonify


def decode_gt(gt):
    """
        Decode compressed genotypes
    """
    return pickle.loads(zlib.decompress(base64.b64decode(gt)))


def get_gt(chrom, pos):
    """
        return GT by chrom and position
    """
    return decode_gt(WI.get(WI.CHROM == chrom, WI.POS == pos).GT)


def fetch_geo_gt(chrom, pos):
    """
        Fetch genotypes with strain geographic information
    """
    gt = get_gt(chrom, pos)
    strain_locations = list(strain.select(strain.isotype,
                                          strain.latitude,
                                          strain.longitude)
                .filter(strain.latitude != None)
                .distinct().dicts().execute())
    strain_locations = {x["isotype"]: x for x in strain_locations}
    for i in gt:
        if i["SAMPLE"] in strain_locations and i["GT"] in ["0/0", "1/1"]:
            gts = {"TGT": i["TGT"], "GT": i["GT"]}
            strain_locations[i["SAMPLE"]].update(gts)
        else:
            if i["SAMPLE"] in strain_locations:
                del strain_locations[i["SAMPLE"]]
    return strain_locations.values()


def gt_from_interval(chrom, start, end, var_eff):
    if var_eff == "ALL":
        var_eff = WI.CHROM == chrom
    else:
        var_eff = (WI.putative_impact << var_eff)
    result = list(WI.select(WI.CHROM,
                            WI.POS,
                            WI.REF,
                            WI.ALT,
                            WI.FILTER,
                            WI.transcript_biotype,
                            WI.putative_impact,
                            WI.gene_name,
                            WI.gene_id,
                            WI.hgvs_p,
                            WI.protein_position,
                            WI.GT,
                            WI.feature_id,
                            WI.annotation)
                    .filter(WI.CHROM == chrom,
                            WI.POS >= start,
                            WI.POS <= end,
                            var_eff) 
                    .limit(1000)
                    .dicts()
                    .execute())
    for i in result:
        i["GT"] = decode_gt(i["GT"])
    return result

@app.route('/api/variant/gt/<string:chrom>/<int:pos>')
def api_get_gt(chrom, pos):
        """
            Retrieve a single genotype.
        """
        gt = get_gt(chrom, pos)
        return jsonify(gt)


@app.route('/api/variant/gtloc/<string:chrom>/<int:pos>')
def strain_gt_locations(chrom, pos):
        """
            Retreive genotypes with location information
        """
        result = fetch_geo_gt(chrom, pos)
        return jsonify(result)



#
# Get Genotypes from Interval
#

@app.route('/api/variant/gt/<string:chrom>/<int:start>/<int:end>/<string:tracks>')
@app.route('/api/variant/gt/<string:chrom>/<int:start>/<int:end>/')
@app.route('/api/variant/gt/<string:chrom>/<int:start>/<int:end>')
def fetch_gt_from_interval(chrom, start, end, tracks="ALL"):
    if tracks != "ALL":
        putative_impact = {'l': 'LOW', 'm': 'MODERATE', 'h': 'HIGH'}
        tracks = [putative_impact[x] if x else '' for x in tracks]
    result = gt_from_interval(chrom, start, end, tracks)
    return jsonify(result)

