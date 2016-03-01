from flask import Flask, Response
from flask_restful import Resource, Api
from cendr import api
from cendr.models import report, mapping, strain
from collections import OrderedDict
import decimal
import json
import datetime
import os, sys


FIELDS = ["strain", "isotype", "warning_message", "use", "sequenced", "previous_names", "source_lab", "latitude","longitude", "landscape", "substrate", "isolated_by", "isolation_date", "isolation_date_comment", "isolation","location", "address", "city", "state", "country", "set_heritability", "set_1", "set_2", "set_3", "set_4","bam_file", "bam_index", "cram_file", "cram_index", "variant_file"]
PEWEE_FIELDS_LIST = [strain.strain, strain.isotype, strain.warning_message, strain.use, strain.sequenced, strain.previous_names, strain.source_lab, strain.latitude, strain.longitude, strain.landscape, strain.substrate, strain.isolated_by, strain.isolation_date, strain.isolation_date_comment, strain.isolation, strain.location, strain.address, strain.city, strain.state, strain.country, strain.set_heritability, strain.set_1, strain.set_2, strain.set_3, strain.set_4, strain.bam_file, strain.bam_index, strain.cram_file, strain.cram_index, strain.variant_file]


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, datetime.date):
            return "G"
        return super(CustomEncoder, self).default(o)

def abort_if_todo_doesnt_exist(request_id):
    if request_id not in TODOS:
        abort(404, message="Doesn't exist".format(request_id))

class mapping_api(Resource):
    def get(self):
        reports = list(mapping.select(mapping.chrom, 
                                      mapping.pos,
                                      mapping.interval_start,
                                      mapping.interval_end,
                                      mapping.log10p,
                                      mapping.variance_explained,
                                      mapping.BF,
                                      mapping.reference,
                                      mapping.version).join(report).filter(report.release==0).tuples().execute())
        
        fields = ["chrom", "pos", "interval_start", "interval_end", "log10p", "variance_explained", "BF", "reference", "version"]
        reports = [OrderedDict(zip(fields, x)) for x in reports]
        dat = json.dumps(reports, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")

class strain_api(Resource):
    def get(self):
        strain_data = list(strain.select(*PEWEE_FIELDS_LIST).tuples().execute())
        strain_data = [OrderedDict(zip(FIELDS, x)) for x in strain_data]
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")


class strain_ind_api(Resource):
    def get(self, strain_name):
        strain_data = list(strain.select(*PEWEE_FIELDS_LIST).filter(strain.strain == strain_name).tuples().execute())
        print strain_data
        strain_data = OrderedDict(zip(FIELDS, strain_data[0]))
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")

class isotype_ind_api(Resource):
    def get(self, isotype_name):
        strain_data = list(strain.select(*PEWEE_FIELDS_LIST).filter(strain.isotype == isotype_name).tuples().execute())
        strain_data = OrderedDict(zip(FIELDS, strain_data[0]))
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")



api.add_resource(mapping_api, '/api/mapping/')
api.add_resource(strain_api, '/api/strain/')
api.add_resource(strain_ind_api, '/api/strain/<string:strain_name>/')
api.add_resource(isotype_ind_api, '/api/isotype/<string:isotype_name>/')
