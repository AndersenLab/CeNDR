import yaml
from base.extensions import cache
from flask import (render_template,
                   request,
                   url_for,
                   redirect,
                   Response,
                   Blueprint,
                   abort,
                   flash,
                   Markup,
                   stream_with_context)

from base.models import Strain
from base.views.api.api_strain import get_strains, query_strains
from base.utils.data_utils import dump_json
from base.utils.gcloud import list_release_files
from os.path import basename
from base.config import config
from logzero import logger

strains_bp = Blueprint('strains',
                      __name__,
                      template_folder='strain')
#
# Strain List Page
#
@strains_bp.route('/')
@cache.memoize(50)
def strains():
    """
        Redirect base route to the strain list page
    """
    disable_parent_breadcrumb = True
    return render_template('strain/strains.html', **locals())

@strains_bp.route('/map')
@cache.memoize(50)
def strains_map():
    """
        Redirect base route to the strain list page
    """
    title = 'Strain Map'
    strains = get_strains()
    strain_listing = [s.to_json() for s in strains]
    return render_template('strain/strains_map.html', **locals())

@strains_bp.route('/isotype_list')
@cache.memoize(50)
def strains_list():
    """
        Strain list of all wild isolates
        within the SQLite database and a table of all strains
    """
    VARS = {
        'title': 'Isotype List',
        'strain_listing': get_strains()}
    return render_template('strain/strains_list.html', **VARS)

@strains_bp.route('/issues')
@cache.memoize(50)
def strains_issues():
    """
        Strain issues shows latest data releases table of strain issues
    """
    VARS = {
        'title': 'Strain Issues',
        'strain_listing_issues': get_strains(issues=True)}
    return render_template('strain/strain_issues.html', **VARS)


@strains_bp.route('/external-links')
@cache.memoize(50)
def external_links():
    """
        Strain issues shows latest data releases table of strain issues
    """
    title = 'External Links'
    return render_template('strain/external_links.html', **locals())


#
# Strain Data
#
@strains_bp.route('/CelegansStrainData.tsv')
def strains_data_tsv():
    """
        Dumps strain dataset; Normalizes lat/lon on the way out.
    """

    def generate():
        col_list = list(Strain.__mapper__.columns)
        col_order = [1, 0, 3, 4, 5, 7, 8, 9, 10, 28, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 2, 6]
        col_list[:] = [col_list[i] for i in col_order]
        header = [x.name for x in col_list]
        yield '\t'.join(header) + "\n"
        for row in query_strains(issues=False):
            row = [getattr(row, column.name) for column in col_list]
            yield '\t'.join(map(str, row)) + "\n"

    return Response(stream_with_context(generate()), mimetype="text/tab-separated-values")


#
# Isotype View
#
@strains_bp.route('/isotype/<isotype_name>/')
@strains_bp.route('/isotype/<isotype_name>/<release>')
@cache.memoize(50)
def isotype_page(isotype_name, release=config['DATASET_RELEASE']):
    """
        Isotype page
    """
    isotype = query_strains(isotype_name=isotype_name)
    if not isotype:
        abort(404)

    # Fetch isotype images
    photos = list_release_files(f"photos/isolation/{isotype_name}")
    photo_set = {}
    for row in photos:
        if 'thumb' not in row:
            strains = basename(row).replace(".jpg", "").split("_")[1:]
            photo_set[row.replace(".jpg", ".thumb.jpg")] = strains

    # High impact variants
    logger.info(release)

    VARS = {"title": f"Isotype {isotype_name}",
            "isotype": isotype,
            "isotype_name": isotype_name,
            "isotype_ref_strain": [x for x in isotype if x.isotype_ref_strain][0],
            "strain_json_output": dump_json(isotype),
            "photo_set": photo_set}
    return render_template('strain/isotype.html', **VARS)


#
# Strain Catalog
#

@strains_bp.route('/catalog', methods=['GET', 'POST'])
@cache.memoize(50)
def strains_catalog():
    flash(Markup("Strain mapping sets 9 and 10 will not be available until later this year."), category="warning")
    title = "Strain Catalog"
    warning = request.args.get('warning')
    strain_listing = get_strains()
    strain_sets = Strain.strain_sets()
    return render_template('strain/strain_catalog.html', **locals())

#
# Strain Submission
#


@strains_bp.route('/submit')
def strains_submission_page():
    """
        Google form for submitting strains
    """
    title = "Strain Submission"
    return render_template('strain/strain_submission.html', **locals())


#
# Protocols
#

@strains_bp.route("/protocols")
@cache.cached(timeout=50)
def protocols():
    title = "Protocols"
    protocols = yaml.load(
        open("base/static/yaml/protocols.yaml", 'r'))
    return render_template('strain/protocols.html', **locals())
