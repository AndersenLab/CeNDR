from cendr import app
from cendr.models import wb_gene, WI, mapping, trait, report
from collections import OrderedDict
from flask import render_template, request, redirect, url_for

#
# Gene View
# 


@app.route('/gene/<gene_name>/')
def gene(gene_name):
    title = gene_name
    tbl_color = {"LOW": 'success', "MODERATE": 'warning', "HIGH": 'danger'}
    bcs = OrderedDict([("Gene", None), (title, None)])

    result = list(wb_gene.filter((wb_gene.Name == gene_name) |
                                  (wb_gene.sequence_name == gene_name) |
                                  (wb_gene.locus == gene_name)).dicts().execute())

    if len(result) != 1:
        return render_template('404.html'), 404

    gene_record = result[0]

    # Retrieve variants
    variants = WI.select().filter(
               WI.CHROM == gene_record["CHROM"],
               WI.gene_id == gene_record["Name"]).dicts().execute()

    # Retrieve mappings
    mapping_set = mapping.select(mapping, trait, report) \
                       .join(trait) \
                       .join(report) \
                       .where((report.release == 0) &
                        (gene_record["start"] >= mapping.interval_start) & 
                        (gene_record["end"] <= mapping.interval_end)) \
                       .dicts() \
                       .execute()



    return render_template('gene.html', **locals())

