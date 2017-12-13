from base import api, cache, app
from peewee import fn, JOIN
from flask import jsonify
from base.models import trait, report, db, mapping
from dateutil.parser import parse
from flask_restful import Resource


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