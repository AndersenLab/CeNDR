from base.models2 import strain_m
from base.application import app
from base.utils.decorators import jsonify_request
from sqlalchemy import or_
from flask import request
from logzero import logger

@app.route('/api/strain/query/<string:query>')
@jsonify_request
def search_strains(query):
    base_query = strain_m.query.filter(strain_m.isotype != None)
    query = query.upper()
    results = base_query.filter(or_(strain_m.isotype == query,
                                    strain_m.isotype.like(f"{query}%"),
                                    strain_m.strain == query,
                                    strain_m.strain.like(f"{query}%"),
                                    strain_m.previous_names.like(f"%{query}|%"),
                                    strain_m.previous_names.like(f"%,{query}|"),
                                    strain_m.previous_names.like(f"%{query}"),
                                    strain_m.previous_names == query))
    results = list([x.to_json() for x in results])
    return results    



@app.route('/api/strain/')
@app.route('/api/strain/<string:strain_name>')
@app.route('/api/strain/isotype/<string:isotype_name>')
@jsonify_request
def query_strains(strain_name=None, isotype_name=None, release=None, all_strain_names=False, resolve_isotype=False):
    """
        Return the full strain database set

        strain_name - Returns data for only one strain
        isotype_name - Returns data for all strains of an isotype
        release - Filters results released prior to release data
        all_strain_names - Return list of all possible strain names (internal use).
        resolve_isotype - Use to search for strains and return their isotype
    """
    base_query = strain_m.query
    if release:
        base_query = base_query.filter(strain_m.release <= release)
    if strain_name or resolve_isotype:
        results = base_query.filter(or_(strain_m.previous_names.like(f"%{strain_name}|%"),
                                        strain_m.previous_names.like(f"%,{strain_name}|"),
                                        strain_m.previous_names.like(f"%{strain_name}"),
                                        strain_m.previous_names == strain_name,
                                        strain_m.strain == strain_name)).first()
    elif isotype_name:
        results = base_query.filter(strain_m.isotype == isotype_name).all()
    else:
        results = base_query.all()

    if all_strain_names:
        previous_strain_names = sum([x.previous_names.split("|") for x in results if x.previous_names], [])
        results = [x.strain for x in results] + previous_strain_names
    if resolve_isotype:
        if results:
            # LSJ1/LSJ2 prev. N2; So N2 needs to be specific.
            if strain_name == 'N2':
                return 'N2'
            return results.isotype
    return results


def get_strains(known_origin=False):
    """
        Returns a list of strains;

        Represents all strains

        Args:
            known_origin: Returns only strains with a known origin
            list_only: Returns a list of isotypes (internal use)
    """
    ref_strain_list = strain_m.query.filter(strain_m.reference_strain == True).all()
    ref_strain_list = {x.isotype: x.strain for x in ref_strain_list}
    result = strain_m.query
    if known_origin or 'origin' in request.path:
        result = result.filter(strain_m.latitude != None)
    result = result.all()
    for strain in result:
        strain.reference_strain = ref_strain_list[strain.isotype]
        logger.error(strain.reference_strain)
    return result


@app.route('/api/isotype')
@app.route('/api/isotype/origin')
@jsonify_request
def get_isotypes(known_origin=False, list_only=False):
    """
        Returns a list of strains when reference_strain == True;

        Represents ONE strain per isotype. This is the reference strain.

        Args:
            known_origin: Returns only strains with a known origin
            list_only: Returns a list of isotypes (internal use)
    """
    result = strain_m.query.filter(strain_m.reference_strain == True) \
                           .order_by(strain_m.reference_strain)
    if known_origin or 'origin' in request.path:
        result = result.filter(strain_m.latitude != None)
    result = result.all()
    if list_only:
        result = [x.isotype for x in result]
    return result
