from base.application import app, cache, releases
from flask import make_response, Response
import requests
from base.models import strain, report, homologene, mapping, trait
from base.views.api.correlation import get_correlated_genes
from collections import OrderedDict
from flask import render_template
from base.views.api.api_strain import get_isotypes, query_strains
from base.constants import RELEASES

#
# Data Page
#


@app.route('/Data/')
@app.route('/data/')
@app.route('/Data/<string:release>')
@app.route('/data/<string:release>')
@cache.memoize(50)
def data_page(release = releases[0]):
    title = "Data"
    strain_listing = query_strains(release=release)
    # Fetch variant data
    url = "https://storage.googleapis.com/elegansvariation.org/releases/{release}/multiqc_bcftools_stats.json".format(release=release)
    vcf_summary = requests.get(url).json()
    VARS = {'title': title,
            'strain_listing': strain_listing,
            'vcf_summary': vcf_summary,
            'RELEASES': RELEASES}
    return render_template('data.html', **VARS)


#
# Download Script
#

@app.route('/data/download/<filetype>.sh')
@cache.memoize(50)
def download_script(filetype):
    strain_listing = query_strains(release=release)
    download_page = render_template('download_script.sh', **locals())
    response = make_response(download_page)
    response.headers["Content-Type"] = "text/plain"
    return response


@app.route('/data/browser/')
@app.route('/data/browser/<region>')
@app.route('/data/browser/<region>/<query>')
def browser(region = "III:11746923-11750250", tracks="mh", query = None):
    title = "Browser" 
    build = releases[0]
    isotype_listing = get_isotypes(list_only=True)
    print(isotype_listing)
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
