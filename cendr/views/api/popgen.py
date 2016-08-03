from flask_restful import Resource
from cendr.models import tajimaD
from flask import jsonify
from cendr import api


class tajima_d(Resource):
    def get(self, chrom, start, end):
        data = list(tajimaD.select(tajimaD.BIN_START, tajimaD.TajimaD)
                           .filter((tajimaD.CHROM == chrom) &
                                   (tajimaD.BIN_START >= start - 50000) &
                                   (tajimaD.BIN_END <= end + 50000),
                                   ).tuples().execute())
        data = [(int(x[0]) + 50000, float(x[1])) for x in data]
        response = {"x": [x[0] for x in data], "y": [x[1] for x in data]}
        return jsonify(response)

api.add_resource(
    tajima_d, '/api/variant/tajima/<string:chrom>/<int:start>/<int:end>')
