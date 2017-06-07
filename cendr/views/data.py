from cendr import app, cache, releases
from cendr import api
from flask import make_response, Response
from cendr.models import strain, report, homologene, mapping, trait
from cendr.views.api.correlation import get_correlated_genes
from collections import OrderedDict
from flask import render_template


@app.route('/Data/')
@app.route('/data/')
@app.route('/Data/<string:release>')
@app.route('/data/<string:release>')
@cache.memoize(50)
def data_page(release = releases[0]):
    from cendr import releases
    bcs = OrderedDict([("Data", None)])
    title = "Data"
    strain_listing = strain.select().filter(
        strain.isotype != None, strain.release <= release).order_by(strain.isotype).execute()
    return render_template('data.html', **locals())


@app.route('/data/download/<filetype>.sh')
@cache.memoize(50)
def download_script(filetype):
    strain_listing = strain.select().filter(
        strain.isotype != None).order_by(strain.isotype).execute()
    download_page = render_template('download_script.sh', **locals())
    response = make_response(download_page)
    response.headers["Content-Type"] = "text/plain"
    return response


@app.route('/data/browser/')
@app.route('/data/browser/<region>')
@app.route('/data/browser/<region>/<query>')
def browser(region = "III:11746923-11750250", tracks="mh", query = None):
    bcs = OrderedDict([("Data", "/data"), ("Browser", None)])
    title = "Browser" 
    from cendr import build
    
    isotype_listing = list(strain.select(strain.isotype).distinct().filter(
                                    strain.isotype != None).order_by(strain.isotype).dicts().execute())
    isotypes = [x["isotype"] for x in isotype_listing]
    
    return render_template('browser.html', **locals())


@app.route('/data/interval/<report_slug>/<trait_slug>')
def interval_download(report_slug, trait_slug):
    """
        Return interval data.
    """
    def generate():
        r = report.get(report_slug = report_slug)
        t = trait.get(report = r, trait_slug = trait_slug)
        intervals = list(report.select(mapping) \
               .join(mapping) \
               .where(
                        (report.report_slug == report_slug)
                        & 
                        (mapping.trait == t)
                    ) \
               .dicts()
               .execute())
        yield "\t".join(["report", "trait", "CHROM_POS", "REF", "ALT",
                         "gene_id", "locus", "feature_id", "transcript_biotype",
                         "annotation", "putative_impact", "hgvs_p", 
                         "correlation"]) + "\n"
        for i in intervals:
            for cor in get_correlated_genes(r, t, i["chrom"], i["interval_start"], i["interval_end"]):
                for variant in cor["variant_set"]:
                    line = map(str, [r.report_slug,
                                     t.trait_slug,
                                     variant["CHROM_POS"], 
                                     variant["REF"],
                                     variant["ALT"],
                                     variant["gene_id"],
                                     cor["gene_name"],
                                     variant["feature_id"],
                                     cor["transcript_biotype"],
                                     variant["annotation"],
                                     variant["putative_impact"],
                                     variant["hgvs_p"],
                                     variant["correlation"]])
                    yield '\t'.join(line) + "\n"

    return Response(generate(), mimetype='text/tab-separated-values')
