from flask_restful import Resource
from cendr import api
from flask import jsonify
from cendr.models import homologene, wb_orthologs, wb_gene


class search_homologs(Resource):
    @cache.memoize(50)
    def get(self, term):
        hgene_results = list(homologene.filter(
                            (homologene.gene_symbol == term) or
                            (homologene.protein_gi == term) or
                            (homologene.protein_accession == term))
            .select(homologene.gene_symbol,
                    homologene.ce_gene_name,
                    homologene.species)
            .distinct()
            .dicts().execute())

        wbgene_results = list(wb_orthologs.filter(
                              (wb_orthologs.gene_symbol == term) or
                              (wb_orthologs.ortholog == term))
                              .select(wb_orthologs.gene_symbol,
                                      wb_orthologs.ce_gene_name,
                                      wb_orthologs.species)
                              .distinct()
                              .dicts().execute())

        for x in hgene_results:
            x.update({"source": "homologene"})
        for x in wbgene_results:
            x.update({"source": "wormbase"})

        homologs = hgene_results + wbgene_results
        # For genes that can't be looked up, fetch coordinates.
        for x in homologs:
            if x["ce_gene_name"].find(".") > 0:
                try:
                    gene = wb_gene.get(
                        wb_gene.sequence_name == x["ce_gene_name"])
                    x.update(
                        {"CHROM": gene.CHROM,
                         "start": gene.start,
                         "end": gene.end})
                except:
                    del x
        result = hgene_results + wbgene_results

        return jsonify(result)


api.add_resource(search_homologs, '/api/homolog/<string:term>')
