from flask import jsonify
from subprocess import Popen, PIPE

from base.constants import GOOGLE_CLOUD_BUCKET
from base.config import config
from base.application import app
from base.views.api.api_variant import variant_query
from base.views.api.api_strain import get_isotypes
from base.utils.decorators import jsonify_request


@app.route('/api/popgen/tajima/<string:chrom>/<int:start>/<int:end>')
@app.route('/api/popgen/tajima/<string:chrom>/<int:start>/<int:end>/<int:release>')
@jsonify_request
def tajima(chrom, start, end, release = config['DATASET_RELEASE']):
    """
        Args:
            chrom
            start
            end

        Output:
            JSON dict of x (position) and y (Tajima's scores) for
            the specified interval.
            {
                "x": [<numeric: position>],
                "y": [<numeric: Tajima's D scores>]
            }

    """
    # No tajima bedfile exists for 20160408 - so use next version.
    if release < 20170531:
        release = 20170531
    url = f"http://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/releases/{release}/popgen/WI.{release}.tajima.bed.gz"
    comm = ['tabix', url, "{chrom}:{start}-{end}".format(**locals())]
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()

    if not out and err:
        return jsonify(error=str(err, encoding='utf-8')), 404
    out = [x.split("\t") for x in str(out, encoding='ascii').splitlines()]
    data = [(int(x[2]) + 50000, float(x[5])) for x in out]
    response = {"x": [x[0] for x in data],
                "y": [x[1] for x in data]}
    return response


@app.route('/api/popgen/gt/<string:chrom>/<int:pos>')
@app.route('/api/popgen/gt/<string:chrom>/<int:pos>/<int:release>')
@jsonify_request
def get_allele_geo(chrom, pos, isotypes=None, release=None):
    """
        Args:
            chrom
            pos
            isotypes
    """
    if release == None:
      release = config['DATASET_RELEASE']
    try:
        variant = variant_query(f"{chrom}:{pos}-{pos+1}", list_all_strains=True, release=release)[0]
    except IndexError:
        return []

    isotypes = get_isotypes(known_origin=True)
    isotypes = {x._asdict()['isotype']: x for x in isotypes}
    for gt in variant['GT']:
        try:
            isotype_loc = {'latitude': isotypes[gt['SAMPLE']].latitude,
                           'longitude': isotypes[gt['SAMPLE']].longitude,
                           'elevation': isotypes[gt['SAMPLE']].elevation}
            gt.update(isotype_loc)
        except KeyError:
            pass
    variant['GT'] = [x for x in variant['GT'] if x.get('latitude')]
    return variant