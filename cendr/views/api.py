from flask import Flask, Response, request
from flask_restful import Resource, Api, reqparse
from cendr import api
from cendr.models import *
from collections import OrderedDict
from gcloud import storage
import decimal
import json
import datetime
import os
import sys
from peewee import JOIN
from dateutil.parser import parse


FIELDS = [x.name for x in strain._meta.sorted_fields if x.name != "id"]
PEEWEE_FIELDS_LIST = [getattr(strain, x.name)
                      for x in strain._meta.sorted_fields if x.name != "id"]


class CustomEncoder(json.JSONEncoder):

    def default(self, o):
        if type(o) == decimal.Decimal:
            return float(o)
        if isinstance(o, datetime.date):
            return str(o)
        return super(CustomEncoder, self).default(o)

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
                                      mapping.version).join(report).filter(report.release == 0).tuples().execute())

        fields = ["chrom", "pos", "interval_start", "interval_end",
                  "log10p", "variance_explained", "BF", "reference", "version"]
        reports = [OrderedDict(zip(fields, x)) for x in reports]
        dat = json.dumps(reports, cls=CustomEncoder, indent=4)
        return Response(response=dat, status=200, mimetype="application/json")


class strain_api(Resource):

    def get(self):
        strain_data = list(strain.select(
            *PEEWEE_FIELDS_LIST).tuples().execute())
        strain_data = [OrderedDict(zip(FIELDS, x)) for x in strain_data]
        dat = json.dumps(strain_data, cls=CustomEncoder, indent=4)
        return Response(response=dat, status=200, mimetype="application/json")


class strain_ind_api(Resource):

    def get(self, strain_name):
        strain_data = list(strain.select(
            *PEEWEE_FIELDS_LIST).filter(strain.strain == strain_name).tuples().execute())
        strain_data = OrderedDict(zip(FIELDS, strain_data[0]))
        dat = json.dumps(strain_data, cls=CustomEncoder, indent=4)
        return Response(response=dat, status=200, mimetype="application/json")


class isotype_ind_api(Resource):

    def get(self, isotype_name):
        strain_data = list(strain.select(
            *PEEWEE_FIELDS_LIST).filter(strain.isotype == isotype_name).tuples().execute())
        strain_data = OrderedDict(zip(FIELDS, strain_data[0]))
        dat = json.dumps(strain_data, cls=CustomEncoder, indent=4)
        return Response(response=dat, status=200, mimetype="application/json")


class report_by_date(Resource):

    def get(self, date):
        print parse(date).date()
        data = list(trait.select(report.report_slug, report.report_name, trait.trait_name, trait.trait_slug, report.release, trait.submission_complete).join(
            report).filter((db.truncate_date("day", trait.submission_complete) == parse(date).date()), (report.release == 0), trait.status == "complete").dicts().execute())
        dat = json.dumps(data, cls=CustomEncoder, indent=4)
        return Response(response=dat, status=200, mimetype="application/json")


class report_progress(Resource):

    def post(self, trait_slug, report_slug=None, report_hash=None):
        queue = get_queue()
        print dir(queue)
        current_status = list(trait.select(trait.status)
                              .join(report)
                              .filter(trait.trait_slug == trait_slug, ((report.report_slug == report_slug) and (report.release == 0)) | (report.report_hash == report_hash))
                              .dicts()
                              .execute())[0]["status"]
        if trait_slug:
            try:
                trait_data = [x for x in report_data if x[
                    'trait_slug'] == trait_slug[0]]
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
            'src="', 'src="' + base_url + "/")

        if not report_html.startswith("<?xml"):
            report_html = report_html[report_html.find("<body>"):report_html.find("</body")].replace(
                "</body", " ").replace("<body>", "").replace('<h1 class="title">cegwas results</h1>', "")
        else:
            report_html = "hello"
        return Response(response=report_html, status=201, mimetype="application/json")

reports_urls = ['/api/<string:report_slug>/<string:trait_slug>',
                '/api/<string:report_slug>/<string:trait_slug>']


class site_gt(Resource):

    def get(self, chrom, pos):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT).join(
            call).filter(site.CHROM == chrom, site.POS == pos).dicts().execute())
        result = json.dumps(result, cls=CustomEncoder, indent=4)
        return Response(response=result, status=201, mimetype="application/json")


class site_gt_range(Resource):

    def get(self, chrom, pos, pos_end):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT).join(
            call).filter(site.CHROM == chrom, site.POS >= pos, site.POS <= pos_end).dicts().execute())
        result = json.dumps(result, cls=CustomEncoder, indent=4)
        return Response(response=result, status=201, mimetype="application/json")


class site_gt_annotation(Resource):

    def get(self, chrom, pos):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT, annotation)
                      .join(call)
                      .switch(site)
                      .join(annotation)
                      .filter(site.CHROM == chrom, site.POS == pos)
                      .dicts()
                      .execute())
        result = json.dumps(result, cls=CustomEncoder, indent=4)
        return Response(response=result, status=201, mimetype="application/json")


class site_gt_range_annotation(Resource):

    def get(self, chrom, pos, pos_end):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT, annotation)
                      .join(call)
                      .switch(site)
                      .join(annotation)
                      .filter(site.CHROM == chrom, site.POS >= pos, site.POS <= pos_end)
                      .dicts()
                      .execute())
        result = json.dumps(result, cls=CustomEncoder, indent=4)
        return Response(response=result, status=201, mimetype="application/json")


class site_gt_invariant_table(Resource):

    def get(self, chrom, pos, interval_start, interval_end, reference):
        result = list(site.select(site.CHROM, site.POS, call.SAMPLE, site.FILTER, call.FT, call.TGT, call.GT, annotation)
                      .join(call)
                      .switch(site)
                      .join(annotation)
                      .filter(site.CHROM == chrom, site.POS >= pos, site.POS <= pos_end)
                      .dicts()
                      .execute())
        result = json.dumps(result, cls=CustomEncoder, indent=4)
        return Response(response=result, status=201, mimetype="application/json")

#
# Tajima's D
#

class tajima_d(Resource):
  def get(self,chrom,start,end):
      data = list(tajimaD.select((tajimaD.BIN_START + 100000)/2,
                                 tajimaD.TajimaD).filter((tajimaD.id % 5 == 0), 
                                                         (tajimaD.CHROM == chrom),
                                                         (((tajimaD.BIN_START + 100000)/2 >=  start) and 
                                                          ((tajimaD.BIN_END + 100000)/2 <= end))
                                                         ).tuples().execute())
      data = [(float(x[0]), float(x[1])) for x in data]
      data = {"x": [x[0] for x in data], "y": [x[1] for x in data]}
      dat = json.dumps(data, cls=CustomEncoder, indent = 4)
      return Response(response=dat, status=200, mimetype="application/json")

api.add_resource(tajima_d, '/api/tajima/<string:chrom>/<int:start>/<int:end>')

#
# wb_gene info
#

class get_gene(Resource):
    def get(self, gene):
        result = list(wb_gene.filter((wb_gene.Name == gene) |
                                (wb_gene.sequence_name == gene) |
                                (wb_gene.locus == gene))
                        .dicts()
                        .execute())
        ordered = OrderedDict()
        if len(result) == 1:
            order = [x.name for x in wb_gene._meta.sorted_fields if x.name != "id"]
            for k in order:
                ordered[k] = result[0][k]
            result = json.dumps(ordered, cls=CustomEncoder, indent=4)
            return Response(response=result, status=201, mimetype="application/json")


class get_gene_count(Resource):
    def get(self, chrom, start, end):
        count_by_type = list(wb_gene.select(wb_gene.biotype,
                                            fn.Count(wb_gene.id).alias('count'))
                            .filter((wb_gene.CHROM == chrom),
                                      (wb_gene.start > start),
                                      (wb_gene.end < end)).group_by(wb_gene.biotype).tuples().execute())
        count = sum([x[1] for x in count_by_type])
        result = OrderedDict((("chrom", chrom),
                    ("start", start),
                    ("end", end),
                    ("total", count)))
        result.update(dict(count_by_type))
        print(result)
        result = json.dumps(result, cls=CustomEncoder, indent=4)
        return Response(response=result, status=201, mimetype="application/json")


class get_gene_list(Resource):
    def get(self, chrom, start, end):
        gene_list = list(wb_gene.select(wb_gene.CHROM,
                                        wb_gene.start,
                                        wb_gene.end,
                                        wb_gene.Name,
                                        wb_gene.sequence_name,
                                        wb_gene.biotype,
                                        wb_gene.locus)
                                        .filter((wb_gene.CHROM == chrom),
                                      (wb_gene.start > start),
                                      (wb_gene.end < end)).tuples().execute())
        wb_gene_fields = [x.name for x in wb_gene._meta.sorted_fields if x.name != "id"]
        gene_list = [OrderedDict(zip(wb_gene_fields, x)) for x in gene_list]
        gene_count = len(gene_list)
        result = OrderedDict((("chrom", chrom),
                    ("start", start),
                    ("end", end),
                    ("count", gene_count),
                    ("list", gene_list)))
        result = json.dumps(result, cls=CustomEncoder, indent=4)
        return Response(response=result, status=201, mimetype="application/json")



api.add_resource(mapping_api, '/api/mapping/')
api.add_resource(strain_api, '/api/strain/')
api.add_resource(strain_ind_api, '/api/strain/<string:strain_name>/')
api.add_resource(isotype_ind_api, '/api/isotype/<string:isotype_name>/')

# Variants
api.add_resource(site_gt, '/api/variants/<string:chrom>/<int:pos>')
api.add_resource(
    site_gt_range, '/api/variants/<string:chrom>/<int:pos>/<int:pos_end>')
api.add_resource(site_gt_invariant_table,
                 '/api/variants/<string:chrom>/<int:pos>/<int:pos_end>')

# Annotations
api.add_resource(site_gt_annotation,
                 '/api/variants/annotation/<string:chrom>/<int:pos>')
api.add_resource(site_gt_range_annotation,
                 '/api/variants/annotation/<string:chrom>/<int:pos>/<int:pos_end>')

# Reports
api.add_resource(report_by_date, '/api/report/date/<string:date>')

# gene table
api.add_resource(get_gene, '/api/gene/<string:gene>')
api.add_resource(get_gene_count, '/api/gene/count/<string:chrom>/<int:start>/<int:end>')
api.add_resource(get_gene_list, '/api/gene/list/<string:chrom>/<int:start>/<int:end>')

#api.add_resource(report_progress, *reports_urls)
