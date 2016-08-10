from flask_restful import Resource
from cendr.models import wb_gene
from cendr import api, cache
from collections import OrderedDict
from flask import jsonify


class get_gene(Resource):
    def get(self, gene):
        result = list(wb_gene.filter((wb_gene.Name == gene) |
                                     (wb_gene.sequence_name == gene) |
                                     (wb_gene.locus == gene))
                      .dicts()
                      .execute())
        ordered = OrderedDict()
        if len(result) == 1:
            order = [x.name for x in
                     wb_gene._meta.sorted_fields
                     if x.name != "id"]
            for k in order:
                ordered[k] = result[0][k]
            return jsonify(result)

api.add_resource(get_gene, '/api/gene/<string:gene>')
