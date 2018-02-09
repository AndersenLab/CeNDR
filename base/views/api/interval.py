from base.application import cache, app
from collections import OrderedDict
from collections import Counter
from collections import defaultdict
from flask import jsonify
import json

from base.constants import RELEASES


# Genes
@cache.memoize(timeout=500)
def get_gene_interval_summary(chrom, start, end, include_list = False):
    """
        Return Gene List and Summarizes
    """
    gene_list = list(wb_gene.select(wb_gene).where(
        ((wb_gene.CHROM == chrom) & (wb_gene.start >= start) & (wb_gene.end <= end)) |
        ((wb_gene.CHROM == chrom) & (wb_gene.start <= start) & (wb_gene.end >= start)) |
        ((wb_gene.CHROM == chrom) & (wb_gene.end >= end) & (wb_gene.end <= start))
    ).dicts().distinct().execute())
    for i in gene_list:
        del i["id"]
    biotype_summary = dict(Counter([x["biotype"] for x in gene_list]))
    result = OrderedDict((("chrom", chrom),
                          ("start", start),
                          ("end", end),
                          ("total", len(gene_list)),
                          ("biotype_summary", biotype_summary)))
    if include_list:
        result["gene_list"] = gene_list
    return result


#@app.route('/api/genelist/<string:chrom>/<int:start>/<int:end>')
#def api_gene_list(chrom, start, end):
#    result = get_gene_interval_summary(chrom, start, end, True)
#    return jsonify(result)


# Variants
@cache.memoize(timeout=500)
def get_variant_count(chrom, start, end, filter=True, release=RELEASES[0]):
    """
        Return the number of variants within an interval
    """
    if filter:
        var_filter = (WI.FILTER == "")
    else:
        var_filter = (1 == 1)
    return WI.select(WI.variant) \
        .filter((WI.CHROM == chrom) &
                (WI.POS >= start) &
                (WI.POS <= end) &
                (var_filter)) \
        .group_by() \
        .distinct().count()

#@app.route('/api/variant/count/<string:chrom>/<int:start>/<int:end>')
#@app.route('/api/variant/count/<string:chrom>/<int:start>/<int:end>/<string:filter>')
#def api_variant_count(chrom, start, end, filter=True):
#    if type(filter) == unicode:
#        filter = {'true': True, 'false': False}[filter.lower()]
#    result = get_variant_count(chrom, start, end, filter)
#    return jsonify(result)


def count_column(q):
    return dict(Counter([x[0] for x in q]))

@cache.memoize(timeout=500)
def biotype_by_genes_w_variants(chrom, start, end):
    q = list(WI.select(WI.transcript_biotype) \
               .filter(WI.gene_id != "",
                  WI.CHROM == chrom,
                  WI.POS >= start,
                  WI.POS <= end,
                  WI.FILTER == "") \
          .group_by(WI.gene_id) \
          .tuples()
          .execute())
    q = count_column(q)
    q["total"] = sum(q.values())
    return q


@cache.memoize(timeout=500)
def variants_in_biotype(chrom, start, end):
    q = list(WI.select(WI.transcript_biotype) \
               .filter(WI.gene_id != "",
                  WI.CHROM == chrom,
                  WI.POS >= start,
                  WI.POS <= end,
                  WI.FILTER == "") \
          .group_by(WI.variant) \
          .tuples()
          .execute())
    q = count_column(q)
    q["total"] = sum(q.values())
    return q

@cache.memoize(timeout=500)
def get_gene_w_impact(chrom, start, end):
    """
        Return Genes with variants of given impact for a given interval
    """
    q_biotype = Counter(list(WI.select(WI.transcript_biotype, WI.putative_impact) \
               .filter(WI.gene_id != "",
                  WI.CHROM == chrom,
                  WI.POS >= start,
                  WI.POS <= end,
                  WI.FILTER == "") \
          .group_by(WI.gene_id, WI.transcript_biotype) \
          .tuples()
          .execute()))
    total = {"LOW": 0, "MODERATE": 0, "HIGH":0}
    for k,v in zip([x[1] for x in q_biotype.keys()], q_biotype.values()):
        total[k] += v
    by_biotype = defaultdict(dict)
    for k,v in q_biotype.items():
        by_biotype[k[1]][k[0]] = v
    response = {}
    response["total"] = total
    response.update(by_biotype)
    return response


@cache.memoize(timeout=500)
def variant_interval_summary(chrom, start, end, release = RELEASES[0]):
    r = {}
    r["chrom"] = chrom
    r["start"] = start
    r["end"] = end
    r["variants"] = get_variant_count(chrom, start, end)
    gene_summary = get_gene_interval_summary(chrom, start, end, False)
    gene_summary = {k:v for k,v in gene_summary.items() if k in ['total', 'biotype_summary']}
    r["gene_biotype"] = gene_summary
    r["gene_w_variants_biotype"] = biotype_by_genes_w_variants(chrom, start, end)
    r["variant_in_biotype"] = variants_in_biotype(chrom, start, end)
    r["gene_by_impact"] = get_gene_w_impact(chrom, start, end)
    return r


@app.route('/api/interval/<string:chrom>/<int:start>/<int:end>')
def get_interval_summary(chrom, start, end, release=RELEASES[0]):
    interval = "{chrom}:{start}-{end}".format(**locals())
    cache_isc = list(isc.filter(isc.interval == interval, isc.release == release).dicts().execute())

    if len(cache_isc) > 0:
        return jsonify(json.loads(cache_isc[0]['summary']))
    else:
        summary = variant_interval_summary(chrom, start, end)
        isc(interval = interval, release = release, summary = json.dumps(summary)).save()
    return jsonify(summary)

