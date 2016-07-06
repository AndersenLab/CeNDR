from cendr import app
from cendr.models import wb_gene
from flask import render_template, request, redirect, url_for

#
# Gene View
# 


@app.route('/gene/<gene_name>/')
def gene(gene_name):
    title = gene_name

    results = list(wb_gene.filter((wb_gene.Name == gene_name) |
                                  (wb_gene.sequence_name == gene_name) |
                                  (wb_gene.locus == gene_name)).dicts().execute())
    if len(results) == 1:
        gene_record = results[0]
        return render_template('gene.html', **locals())
    else:
        return render_template('404.html'), 404

