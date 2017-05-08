from cendr import app, cache
from flask import jsonify
from cendr.models import homologene, wb_orthologs, wb_gene


def gene_search(gene, search = False):
    if search:
        results = list(wb_gene.filter((wb_gene.Name.startswith(gene)) |
                                     (wb_gene.sequence_name == gene) |
                                     (wb_gene.locus.startswith(gene)))
                             .dicts()
                             .execute())
        for i in results:
            del i['id']
        return results
    else: 
        result = list(wb_gene.filter((wb_gene.Name == gene) |
                                     (wb_gene.sequence_name == gene) |
                                     (wb_gene.locus == gene))
                             .dicts()
                             .execute())
        del result[0]['id']
        if len(result) == 1:
            return result[0]
    return None

@app.route('/api/gene/<string:gene>')
def api_get_gene(gene):
    return jsonify(gene_search(gene))


@cache.memoize(50)
@app.route('/api/gene/search/<string:term>')
def api_browser_search(term):
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

    # Get gene results
    gene_results = gene_search(term, search=True)
    results []
    for i in gene_results:
        results.append(
            {"CHROM": i['CHROM'],})

    return jsonify(result)
