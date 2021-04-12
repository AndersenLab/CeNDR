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

strain_bp = Blueprint('strain',
                      __name__,
                      template_folder='strain')

#
# Global Strain Map
#
@strain_bp.route('/')
def strain():
    """
        Redirect base route to the global strain map
    """
    return redirect(url_for('strain.map_page'))


@strain_bp.route('/global-strain-map')
@cache.memoize(50)
def map_page():
    """
        Global strain map shows the locations of all wild isolates
        within the SQLite database.
    """
    VARS = {'title': "Global Strain Map",
            'strain_listing': dump_json(get_strains(known_origin=True))}
    return render_template('strain/global_strain_map.html', **VARS)


#
# Strain Data
#

@strain_bp.route('/CelegansStrainData.tsv')
def strain_data_tsv():
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
@strain_bp.route('/isotype/<isotype_name>/')
@strain_bp.route('/isotype/<isotype_name>/<release>')
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

@strain_bp.route('/catalog', methods=['GET', 'POST'])
@cache.memoize(50)
def strain_catalog():
    flash(Markup("Strain mapping sets 7 and 8 will not be available until later this year."), category="warning")
    VARS = {"title": "Strain Catalog",
            "warning": request.args.get('warning'),
            "strain_listing": get_strains(),
            "strain_sets": Strain.strain_sets() }
    return render_template('strain/strain_catalog.html', **VARS)

#
# Strain Submission
#


@strain_bp.route('/submit')
def strain_submission_page():
    """
        Google form for submitting strains
    """
    title = "Strain Submission"
    return render_template('strain/strain_submission.html', **locals())


#
# Protocols
#

@strain_bp.route("/protocols")
@cache.cached(timeout=50)
def protocols():
    title = "Protocols"
    protocols = yaml.load(
        open("base/static/yaml/protocols.yaml", 'r'))
    return render_template('strain/protocols.html', **locals())
