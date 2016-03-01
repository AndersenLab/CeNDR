from flask import Flask, Response
from flask_restful import Resource, Api
from cendr import api
from cendr.models import report, mapping, strain
from collections import OrderedDict
import decimal
import json
import datetime
import os, sys

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
        strain_data = list(strain.select().dicts().execute())
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")

class isotype_ind_api(Resource):
    def get(self, isotype_name):
        strain_data = list(strain.select().filter(strain.isotype == isotype_name).dicts().execute())
        print strain_data
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")


class strain_ind_api(Resource):
    def get(self, strain_name):
        strain_data = strain.select().filter(strain.strain == strain_name).dicts().execute()
        dat = json.dumps(strain_data.next(), cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")


api.add_resource(mapping_api, '/api/mapping/')
api.add_resource(strain_api, '/api/strain/')
api.add_resource(strain_ind_api, '/api/strain/<string:strain_name>/')
api.add_resource(isotype_ind_api, '/api/isotype/<string:isotype_name>/')
