from cendr import app
from cendr.models import wb_gene, WI
from flask import render_template, request, redirect, url_for

#
# Gene View
# 


@app.route('/gene/<gene_name>/')
def gene(gene_name):
    title = gene_name

    result = list(wb_gene.filter((wb_gene.Name == gene_name) |
                                  (wb_gene.sequence_name == gene_name) |
                                  (wb_gene.locus == gene_name)).dicts().execute())

    if len(result) != 1:
        return render_template('404.html'), 404

    gene_record = result[0]

    variants = WI.select(WI.CHROM,
                         WI.POS,
                         WI.gene_id,
                         WI.gene_name).filter(
                         WI.CHROM == gene_record["CHROM"],
                         WI.gene_id == gene_record["Name"]).dicts().execute()

    return render_template('gene.html', **locals())

