from flask_restful import Resource
from cendr.models import WI, mapping_correlation
from cendr import api
from peewee import *
from collections import OrderedDict
from collections import Counter
from collections import defaultdict
from flask import jsonify


def get_correlated_genes(r, t, chrom, start, end):
    print(r)
    print(t)
    # Fetch the maximally correlated genes.
    max_corr = list(mapping_correlation.select(
                        fn.CONCAT(WI.CHROM, ":", WI.POS).alias("CHROM_POS"),
                        fn.MAX(fn.ABS(mapping_correlation.correlation)).alias("max_corr"),
                        fn.COUNT(fn.DISTINCT(WI.variant)).alias("n_variants"),
                        WI.gene_id,
                        WI.gene_name,
                        WI.transcript_biotype) \
                       .group_by(WI.gene_id) \
                       .join(WI, on = (mapping_correlation.CHROM == WI.CHROM) &
                                       (mapping_correlation.POS == WI.POS)) \
                       .where(mapping_correlation.report == r,
                               mapping_correlation.trait == t,
                               mapping_correlation.CHROM == chrom,
                               mapping_correlation.POS >= start,
                               mapping_correlation.POS <= end) \
                       .order_by(-fn.MAX(fn.ABS(mapping_correlation.correlation)), fn.ABS(mapping_correlation.correlation)) \
                       .dicts().execute())
    # Fetch maximally correlated variants
    av = list(mapping_correlation.select(
                        fn.CONCAT(WI.CHROM, ":", WI.POS).alias("CHROM_POS"),
                        mapping_correlation.correlation,
                        WI.gene_id,
                        WI.variant,
                        WI.putative_impact,
                        WI.annotation,
                        WI.REF,
                        WI.ALT,
                        WI.hgvs_p,
                        WI.feature_id) \
                        .group_by(WI.variant) \
                       .join(WI, on = (mapping_correlation.CHROM == WI.CHROM) &
                                       (mapping_correlation.POS == WI.POS)) \
                       .where(mapping_correlation.report == r,
                               mapping_correlation.trait == t,
                               mapping_correlation.CHROM == chrom,
                               mapping_correlation.POS >= start,
                               mapping_correlation.POS <= end) \
                       .order_by(-fn.MAX(fn.ABS(mapping_correlation.correlation))) \
                       .dicts().execute())
    av_set = {}
    for i in av:
        if i["gene_id"] not in av_set:
            av_set[i["gene_id"]] = []
        av_set[i["gene_id"]].append(i)
    for gene in max_corr:
        if gene["gene_id"] in av_set:
            gene["variant_set"] = av_set[gene["gene_id"]]
        else:
            gene["variant_set"] = []
    return max_corr


class get_mapping_correlation(Resource):
    def get(self, report, trait):
        interval = get_correlated_genes(report, trait)
        return jsonify(interval)


api.add_resource(get_mapping_correlation,
                 '/api/correlation/<string:report>/<string:trait>')

