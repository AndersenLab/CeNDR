from flask import json, jsonify
from base.models import strain
from base.models2 import strain_m
from base.application import app, cache
from collections import OrderedDict
from logzero import logger

FIELDS = [x.name for x in strain._meta.sorted_fields if x.name != "id"]
PEEWEE_FIELDS_LIST = [getattr(strain, x.name)
                      for x in strain._meta.sorted_fields if x.name != "id"]


@app.route('/api/strain')
@cache.memoize(50)
def strain_api():
    """
        Return information for all strains.
    """
    strain_data = list(strain.select(
        *PEEWEE_FIELDS_LIST).tuples().execute())
    response = [OrderedDict(zip(FIELDS, x)) for x in strain_data]
    return jsonify(response)


@app.route('/api/strain/<string:strain_name>')
@cache.memoize(50)
def strain_ind_api(strain_name):
    """
        Return information for an individual strain.
    """
    strain_data = list(strain.select(
        *PEEWEE_FIELDS_LIST).filter(strain.strain == strain_name)
                            .tuples()
                            .execute())
    response = OrderedDict(zip(FIELDS, strain_data[0]))
    return jsonify(response)


@app.route('/api/isotype')
def get_reference_strains(known_origin=False):
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
                                          strain_m.longitude) \
                           .filter(strain_m.reference_strain == True, strain_m.latitude != None) \
                           .all()
    return json.dumps(result)



@app.route('/api/strain/isotype/<string:isotype_name>')
@cache.memoize(50)
def isotype_ind_api(isotype_name):
    """
        Return all strains within an isotype.
    """
    strain_data = list(strain.select(
        strain.strain).filter(strain.isotype == isotype_name).execute())
    response = [x.strain for x in strain_data]
    return jsonify(response)
