from base.application import cache, app
from peewee import fn, JOIN
from flask import jsonify
from dateutil.parser import parse
from flask_restful import Resource
from base.utils.gcloud import query_item
from flask import Response

@app.route('/api/report/date/<date>')
def report_by_date(date):
    data = list(trait.select(report.report_slug,
                             report.report_name,
                             trait.trait_name,
                             trait.trait_slug,
                             report.release,
                             trait.submission_date,
                             mapping.log10p,
                             fn.CONCAT(mapping.chrom, ":", mapping.pos).alias("CHROM_POS")) \
                .join(mapping, JOIN.LEFT_OUTER) \
                .switch(trait) \
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



@app.route('/api/report/data/<string:report_slug>')
def report_data(report_slug):
    trait_set = query_item('trait', filters=[('report_slug', '=', report_slug)])

    # Get first report if available.
    try:
        trait = trait_set[0]
    except IndexError:
        try:
            trait_set = query_item('trait', filters=[('secret_hash', '=', report_slug)])
            trait = trait_set[0]
        except IndexError:
            flash('Cannot find report', 'danger')
            return abort(404)

    return Response(trait['trait_data'], mimetype="text/csv", headers={"Content-disposition":"attachment; filename=%s.tsv" % report_slug})
