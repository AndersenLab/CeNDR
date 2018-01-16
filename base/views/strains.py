from base.application import (cache,
                              add_to_order_ws,
                              lookup_order,
                              send_mail)
from flask import render_template, request, url_for, redirect, Response
from base.models2 import strain_m
import yaml
from flask import Blueprint
from base.views.api.api_strain import get_isotypes, query_strains
from base.utils.data_utils import dump_json

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


@strain_bp.route('/global-strain-map/')
@cache.memoize(50)
def map_page():
    """
        Global strain map shows the locations of all wild isolates
        within the SQLite database.
    """
    VARS = {'title': "Global Strain Map",
            'strain_listing': dump_json(get_isotypes(known_origin=True))}
    return render_template('strain/global_strain_map.html', **VARS)


#
# Strain Data
#


@strain_bp.route('/strain_data.tsv')
def strain_metadata():
    """
        Dumps strain dataset; Normalizes lat/lon on the way out.
    """
    col_list = list(strain_m.__mapper__.columns)
    def generate():
        first = True
        if first:
            first = False
            header = [x.name for x in list(strain_m.__mapper__.columns)]
            yield ('\t'.join(header) + "\n").encode('utf-8')
        for row in query_strains():
            row = [getattr(row, column.name) for column in col_list]
            yield ('\t'.join(map(str, row)) + "\n").encode('utf-8')
    return Response(generate(), mimetype="text/tab-separated-values")


#
# Isotype View
#

@strain_bp.route('/isotype/<isotype_name>/')
@cache.memoize(50)
def isotype_page(isotype_name):
    isotype = query_strains(isotype_name = isotype_name)
    VARS = {"title": isotype_name,
            "isotype": isotype,
            "isotype_name": isotype_name,
            "reference_strain": [x for x in isotype if x.reference_strain][0],
            "strain_json_output": dump_json(isotype)}
    return render_template('strain/strain.html', **VARS)


#
# Strain Catalog
#

@strain_bp.route('/catalog')
@cache.memoize(50)
def strain_catalog():
    VARS = {"title": "Strain Catalog",
            "warning": request.args.get('warning'),
            "strain_listing": query_strains()}
    return render_template('strain/strain_catalog.html', **VARS)

#
# Strain Submission
#


@strain_bp.route('/submit/')
def strain_submission_page():
    """
        Google form for submitting strains
    """
    title = "Strain Submission"
    return render_template('strain/strain_submission.html', **locals())


#
# Protocols
#

@strain_bp.route("/protocols/")
@cache.cached(timeout=50)
def protocols():
    title = "Protocols"
    protocols = yaml.load(
        open("base/static/yaml/protocols.yaml", 'r'))
    return render_template('strain/protocols.html', **locals())

