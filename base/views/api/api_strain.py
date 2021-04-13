from base.models import Strain
from base.utils.decorators import jsonify_request
from sqlalchemy import or_
from flask import request
from logzero import logger

from flask import Blueprint

api_strain_bp = Blueprint('api_strain',
                          __name__,
                          template_folder='api')


@api_strain_bp.route('/strain/query/<string:query>')
@jsonify_request
def search_strains(query):
    base_query = Strain.query.filter(Strain.isotype != None)
    query = query.upper()
    results = base_query.filter(or_(Strain.isotype == query,
                                    Strain.isotype.like(f"{query}%"),
                                    Strain.strain == query,
                                    Strain.strain.like(f"{query}%"),
                                    Strain.previous_names.like(f"%{query},%"),
                                    Strain.previous_names.like(f"%,{query},"),
                                    Strain.previous_names.like(f"%{query}"),
                                    Strain.previous_names == query))
    return list([x.to_json() for x in results])


@api_strain_bp.route('/strain/')
@api_strain_bp.route('/strain/<string:strain_name>')
@api_strain_bp.route('/strain/isotype/<string:isotype_name>')
@jsonify_request
def query_strains(strain_name=None, isotype_name=None, release=None, all_strain_names=False, resolve_isotype=False, issues=False, is_sequenced=False):
    """
        Return the full strain database set

        strain_name - Returns data for only one strain
        isotype_name - Returns data for all strains of an isotype
        release - Filters results released prior to release data
        all_strain_names - Return list of all possible strain names (internal use).
        resolve_isotype - Use to search for strains and return their isotype
    """
    query = Strain.query
    if release:
        query = query.filter(Strain.release <= release)
    if strain_name or resolve_isotype:
        query = query.filter(or_(Strain.previous_names.like(f"%{strain_name},%"),
                                        Strain.previous_names.like(f"%,{strain_name},"),
                                        Strain.previous_names.like(f"%{strain_name}"),
                                        Strain.previous_names == strain_name,
                                        Strain.strain == strain_name)).first()
    elif isotype_name:
        query = query.filter(Strain.isotype == isotype_name)
    else:
        query = query

    if is_sequenced is True:
        query = query.filter(Strain.sequenced == True)

    if issues is False:
        query = query.filter(Strain.issues == False)
        query = query.filter(Strain.isotype != None)
        query = query.all()
    else:
        query = query.all()

    if all_strain_names:
        previous_strain_names = sum([x.previous_names.split(",") for x in query if x.previous_names], [])
        results = [x.strain for x in query] + previous_strain_names
    if resolve_isotype:
        if query:
            # LSJ1/LSJ2 prev. N2; So N2 needs to be specific.
            if strain_name == 'N2':
                return 'N2'
            return query.isotype
    return query


def get_strains(known_origin=False, issues=False):
    """
        Returns a list of strains;

        Represents all strains

        Args:
            known_origin: Returns only strains with a known origin
            issues: Return only strains without issues
    """
    ref_strain_list = Strain.query.filter(Strain.isotype_ref_strain == True).all()
    ref_strain_list = {x.isotype: x.strain for x in ref_strain_list}
    result = Strain.query
    if known_origin or 'origin' in request.path:
        result = result.filter(Strain.latitude != None)

    if issues is False:
        result = result.filter(Strain.isotype != None)
        result = result.filter(Strain.issues == False)

    result = result.all()
    for strain in result:
        # Set an attribute for the reference strain of every strain
        strain.reference_strain = ref_strain_list.get(strain.isotype, None)
    return result


@api_strain_bp.route('/isotype')
@api_strain_bp.route('/isotype/origin')
@jsonify_request
def get_isotypes(known_origin=False, list_only=False):
    """
        Returns a list of strains when isotype_ref_strain == True;

        Represents ONE strain per isotype. This is the reference strain.

        Args:
            known_origin: Returns only strains with a known origin
            list_only: Returns a list of isotypes (internal use)
    """
    result = Strain.query.filter(Strain.isotype_ref_strain == True) \
                           .order_by(Strain.isotype)
    if known_origin or 'origin' in request.path:
        result = result.filter(Strain.latitude != None)
    result = result.all()
    if list_only:
        result = [x.isotype for x in result]
    return result
