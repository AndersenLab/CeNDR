from cendr import api, cache
from flask import jsonify
from cendr.models import trait, report, db
from dateutil.parser import parse
from flask_restful import Resource


class report_by_date(Resource):

    def get(self, date):
        data = list(trait.select(report.report_slug,
                                 report.report_name,
                                 trait.trait_name,
                                 trait.trait_slug,
                                 report.release,
                                 trait.submission_date) \
                    .join(report) \
                    .filter(
            (db.truncate_date("day", trait.submission_date) == parse(date).date()
             ),
            (report.release == 0),
            (trait.status == "complete")
            ) \
            .dicts()
            .execute())
        return jsonify(data)

api.add_resource(report_by_date, '/api/report/date/<string:date>')


#class report_progress(Resource):
#
#    def post(self, trait_slug, report_slug=None, report_hash=None):
#        queue = get_queue()
#        current_status = list(trait.select(trait.status)
#                              .join(report)
#                              .filter(trait.trait_slug == trait_slug, ((report.report_slug == report_slug) and (report.release == 0)) | (report.report_hash == report_hash))
#                              .dicts()
#                              .execute())[0]["status"]
#        if trait_slug:
#            try:
#                trait_data = [x for x in report_data if x[
#                    'trait_slug'] == trait_slug[0]]
#            except:
#                return Response(response="", status=404, catch_all_404s=True)
#            title = trait_data["report_name"]
#            subtitle = trait_data["trait_name"]
#
#            if trait_data["release"] == 0:
#                report_url_slug = trait_data["report_slug"]
#            else:
#                report_url_slug = trait_data["report_hash"]
#        else:
#
#            try:
#                first_trait = list(report_data)[0]
#            except:
#                return Response(response="", status=404, catch_all_404s=True)
#
#        report_slug = trait_data["report_slug"]
#        base_url = "https://storage.googleapis.com/cendr/" + report_slug + "/" + trait_slug
#
#        report_files = list(storage.Client().get_bucket("cendr").list_blobs(
#            prefix=report_slug + "/" + trait_slug + "/tables"))
#        report_files = [os.path.split(x.name)[1] for x in report_files]
#
#        report_url = base_url + "/report.html"
#        report_html = requests.get(report_url).text.replace(
#            'src="', 'src="' + base_url + "/")
#
#        if not report_html.startswith("<?xml"):
#            report_html = report_html[report_html.find("<body>"):report_html.find("</body")].replace(
#                "</body", " ").replace("<body>", "").replace('<h1 class="title">cegwas results</h1>', "")
#        else:
#            report_html = ""
#        return Response(response=report_html, status=200, mimetype="application/json")
#
#status_urls = ['/api/<string:report_slug>/<string:trait_slug>',
#                '/api/<string:report_slug>/<string:trait_slug>']
#
#
#api.add_resource(report_progress, status_urls)
#
#