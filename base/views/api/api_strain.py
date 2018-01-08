from base.models import strain
from base.models2 import strain_m
from base.application import app
from base.utils.decorators import jsonify_request


@app.route('/api/strain')
@app.route('/api/strain/<string:strain_name>')
@app.route('/api/isotype/<string:isotype_name>')
@jsonify_request
def query_strains(strain_name=None, isotype_name=None, release=None):
    """
        Return the full strain database set

        strain_name - Returns data for only one strain
        isotype_name - Returns data for all strains of an isotype
        release - Filters results released prior to release data
    """
    base_query = strain_m.query
    if release:
        base_query = base_query.filter(strain_m.release <= release)

    if strain_name:
        results = base_query.filter(strain_m.strain == strain_name).first()
    elif isotype_name:
        results = base_query.filter(strain_m.isotype == isotype_name).all()
    else:
        results = base_query.all()
    return results


@app.route('/api/isotype')
@jsonify_request
def get_isotypes(known_origin=False, list_only=False):
    """
        Returns a list of strains when reference_strain == True;

        Represents ONE strain per isotype. This is the reference strain.

        Args:
            known_origin: Returns only strains with a known origin
            list_only: Returns a list of isotypes (internal use)
    """
    if list_only:
        result = strain_m.query.with_entities(strain_m.isotype) \
                               .filter(strain_m.reference_strain == True, strain_m.latitude != None) \
                               .all()
        result = [x for tupl in result for x in tupl]
    else:
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
    return result