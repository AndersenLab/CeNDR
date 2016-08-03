from flask_restful import Resource
from cendr.models import strain
from cendr import api
from flask import jsonify
from collections import OrderedDict

FIELDS = [x.name for x in strain._meta.sorted_fields if x.name != "id"]
PEEWEE_FIELDS_LIST = [getattr(strain, x.name)
                      for x in strain._meta.sorted_fields if x.name != "id"]


class strain_api(Resource):
    def get(self):
        """
            Return information for all strains.
        """
        strain_data = list(strain.select(
            *PEEWEE_FIELDS_LIST).tuples().execute())
        response = [OrderedDict(zip(FIELDS, x)) for x in strain_data]
        return jsonify(response)


api.add_resource(strain_api, '/api/strain')


class strain_ind_api(Resource):
    def get(self, strain_name):
        """
            Return information for an individual strain.
        """
        strain_data = list(strain.select(
            *PEEWEE_FIELDS_LIST).filter(strain.strain == strain_name)
                                .tuples()
                                .execute())
        response = OrderedDict(zip(FIELDS, strain_data[0]))
        print response, "RESPONSE"
        return jsonify(response)


api.add_resource(strain_ind_api, '/api/strain/<string:strain_name>')


class isotype_ind_api(Resource):
    def get(self, isotype_name):
        """
            Return all strains within an isotype.
        """
        strain_data = list(strain.select(
            strain.strain).filter(strain.isotype == isotype_name).execute())
        response = [x.strain for x in strain_data]
        return jsonify(response)


api.add_resource(isotype_ind_api, '/api/strain/isotype/<string:isotype_name>')
