from flask import jsonify
from base.application import app
from subprocess import Popen, PIPE
from base.constants import DATASET_RELEASE
from base.views.api.api_variant import variant_query
from base.views.api.api_strain import get_isotypes
from base.utils.decorators import jsonify_request


@app.route('/api/popgen/tajima/<string:chrom>/<int:start>/<int:end>')
@jsonify_request
def tajima(chrom, start, end):
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
    url = "http://storage.googleapis.com/elegansvariation.org/releases/{DATASET_RELEASE}/tajima/WI.{DATASET_RELEASE}.tajima.bed.gz".format(DATASET_RELEASE=DATASET_RELEASE)
    comm = ['tabix', url, "{chrom}:{start}-{end}".format(**locals())]
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()

    if err:
        return jsonify(error=str(err, encoding='utf-8')), 404
    out = [x.split("\t") for x in str(out, encoding='ascii').splitlines()]
    data = [(int(x[2]) + 50000, float(x[5])) for x in out]
    response = {"x": [x[0] for x in data],
                "y": [x[1] for x in data]}
    return response


@app.route('/api/popgen/gt/<string:chrom>/<int:pos>')
@jsonify_request
def get_allele_geo(chrom, pos, isotypes=None):
    """
        Args:
            chrom
            pos
            isotypes
    """
    try:
        variant = variant_query(f"{chrom}:{pos}-{pos+1}", list_all_strains=True)[0]
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