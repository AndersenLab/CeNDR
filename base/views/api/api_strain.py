from flask import json, jsonify, request
from base.models import strain
from base.models2 import strain_m
from base.application import app, cache
from collections import OrderedDict
from logzero import logger
from base.utils.decorators import jsonify_request

FIELDS = [x.name for x in strain._meta.sorted_fields if x.name != "id"]
PEEWEE_FIELDS_LIST = [getattr(strain, x.name)
                      for x in strain._meta.sorted_fields if x.name != "id"]


@app.route('/api/strain')
@app.route('/api/strain/<string:strain_name>')
@app.route('/api/isotype/<string:isotype_name>')
@jsonify_request
def get_all_strains(strain_name=None, isotype_name=None):
    """
        Return the full strain database set
    """
    if strain_name:
        results = strain_m.query.filter(strain_m.strain == strain_name).first()
    elif isotype_name:
        results = strain_m.query.filter(strain_m.isotype == isotype_name).all()
    else:
        results = strain_m.query.all()
    return results


@app.route('/api/isotype')
def get_isotypes(known_origin=False):
    """
        Returns a list of strains.
        ONE strain per isotype. This is the reference strain.

        Args:
            known_origin: Returns only strains with a known origin
    """
    result = strain_m.query.with_entities(strain_m.strain,
                                          strain_m.reference_strain,
                                          strain_m.isotype,
                                          strain_m.latitude,
                                          strain_m.longitude,
                                          strain_m.release,
                                          strain_m.isolation_date,
                                          strain_m.elevation,
                                          strain_m.substrate,
                                          strain_m.landscape,
                                          strain_m.sampled_by) \
                           .filter(strain_m.reference_strain == True, strain_m.latitude != None) \
                           .all()
    return jsonify(result)