from flask import Flask, Response,request
from flask_restful import Resource, Api,reqparse
from cendr import api
from cendr.models import report, mapping, strain, trait, site, call, annotation
from collections import OrderedDict
from gcloud import storage
import decimal
import json
import datetime
import os, sys
from peewee import JOIN


FIELDS = [x.name for x in strain._meta.sorted_fields if x.name != "id"]
PEEWEE_FIELDS_LIST = [getattr(strain, x.name) for x in strain._meta.sorted_fields if x.name != "id"]

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


parser = reqparse.RequestParser()

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
        strain_data = list(strain.select(*PEEWEE_FIELDS_LIST).tuples().execute())
        strain_data = [OrderedDict(zip(FIELDS, x)) for x in strain_data]
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")


class strain_ind_api(Resource):
    def get(self, strain_name):
        strain_data = list(strain.select(*PEEWEE_FIELDS_LIST).filter(strain.strain == strain_name).tuples().execute())
        strain_data = OrderedDict(zip(FIELDS, strain_data[0]))
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")

class isotype_ind_api(Resource):
    def get(self, isotype_name):
        strain_data = list(strain.select(*PEEWEE_FIELDS_LIST).filter(strain.isotype == isotype_name).tuples().execute())
        strain_data = OrderedDict(zip(FIELDS, strain_data[0]))
        dat = json.dumps(strain_data, cls=CustomEncoder, indent = 4)
        return Response(response=dat, status=200, mimetype="application/json")



class report_progress(Resource):
    def post(self,trait_slug, report_slug = None,report_hash = None):
      queue = get_queue()
      print dir(queue)
      current_status = list(trait.select(trait.status)
                            .join(report)
                            .filter(trait.trait_slug == trait_slug, ((report.report_slug == report_slug) and (report.release == 0)) | (report.report_hash == report_hash))
                            .dicts()
                            .execute())[0]["status"]
      if trait_slug:
        try:
          trait_data = [x for x in report_data if x['trait_slug'] == trait_slug[0]]
        except:
          return Response(response="", status=404, catch_all_404s=True)
        title = trait_data["report_name"]
        subtitle = trait_data["trait_name"]

        if trait_data["release"] == 0:
          report_url_slug = trait_data["report_slug"]
        else:
          report_url_slug = trait_data["report_hash"]
      else:

        try:
          first_trait = list(report_data)[0]
        except:
          return Response(response="", status=404, catch_all_404s=True)

      report_slug = trait_data["report_slug"]
      base_url = "https://storage.googleapis.com/cendr/" + report_slug + "/" + trait_slug
      
      report_files = list(storage.Client().get_bucket("cendr").list_blobs(
        prefix=report_slug + "/" + trait_slug + "/tables"))
      report_files = [os.path.split(x.name)[1] for x in report_files]

      report_url = base_url + "/report.html"
      report_html = requests.get(report_url).text.replace(
        'src="', 'src="'+ base_url + "/")
      
      if not report_html.startswith("<?xml"):
        report_html = report_html[report_html.find("<body>"):report_html.find("</body")].replace("</body", " ").replace("<body>","").replace('<h1 class="title">cegwas results</h1>', "")
      else:
        report_html = "hello"
      return Response(response=report_html, status = 201, mimetype="application/json")

reports_urls = ['/api/<string:report_slug>/<string:trait_slug>','/api/<string:report_slug>/<string:trait_slug>']


class site_gt(Resource):
    def get(self, chrom, pos):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT).join(call).filter(site.CHROM == chrom, site.POS == pos).dicts().execute())
        result = json.dumps(result, cls=CustomEncoder, indent = 4)
        return Response(response=result, status = 201, mimetype="application/json")

class site_gt_range(Resource):
    def get(self, chrom, pos, pos_end):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT).join(call).filter(site.CHROM == chrom, site.POS >= pos, site.POS <= pos_end).dicts().execute())
        result = json.dumps(result, cls=CustomEncoder, indent = 4)
        return Response(response=result, status = 201, mimetype="application/json")

class site_gt_annotation(Resource):
    def get(self, chrom, pos):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT, annotation)
                        .join(call)
                        .switch(site)
                        .join(annotation)
                        .filter(site.CHROM == chrom, site.POS == pos)
                        .dicts()
                        .execute())
        result = json.dumps(result, cls=CustomEncoder, indent = 4)
        return Response(response=result, status = 201, mimetype="application/json")

class site_gt_range_annotation(Resource):
    def get(self, chrom, pos, pos_end):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT, annotation)
                        .join(call)
                        .switch(site)
                        .join(annotation)
                        .filter(site.CHROM == chrom, site.POS >= pos, site.POS <= pos_end)
                        .dicts()
                        .execute())
        result = json.dumps(result, cls=CustomEncoder, indent = 4)
        return Response(response=result, status = 201, mimetype="application/json")


api.add_resource(mapping_api, '/api/mapping/')
api.add_resource(strain_api, '/api/strain/')
api.add_resource(strain_ind_api, '/api/strain/<string:strain_name>/')
api.add_resource(isotype_ind_api, '/api/isotype/<string:isotype_name>/')

# Variants
api.add_resource(site_gt, '/api/variants/<string:chrom>/<int:pos>')
api.add_resource(site_gt_range, '/api/variants/<string:chrom>/<int:pos>/<int:pos_end>')

# Annotations
api.add_resource(site_gt_annotation, '/api/variants/annotation/<string:chrom>/<int:pos>')
api.add_resource(site_gt_range_annotation, '/api/variants/annotation/<string:chrom>/<int:pos>/<int:pos_end>')

#api.add_resource(report_progress, *reports_urls)