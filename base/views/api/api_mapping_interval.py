#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

This file provides output from mapping intervals for use in plotting fine-mapping results

"""
import re
import json
from flask import jsonify
from logzero import logger
from base.application import app
from base.models2 import trait_m
from base.utils.decorators import jsonify_request
from base.utils.gcloud import query_item

impact_colors = {'LOW': '#98f094',
                 'MODERATE': '#fbf3a1',
                 'HIGH': '#ed9693',
                 'MODIFIER': '#f7f7f7'}

@app.route('/api/trait/mapping/<string:report_slug>/<string:trait_name>/<string:peak>', methods=["GET", "POST"])
def mapping_interval(report_slug, trait_name, peak):
    try:
        trait = query_item('trait', filters=[('report_trait', '=', f"{report_slug}:{trait_name}")])[0]
    except IndexError:
        err = f"Report - Trait not found: {report_slug}:{trait_name}"
        logger.error(err)
        return err, 404
    trait = trait_m(trait.key.name)
    interval_summary = trait.get_gs_as_dataset("interval_variants.tsv.gz").fillna("")
    interval_summary = interval_summary[interval_summary.peak == peak.replace("_", ":")]
    interval_summary = interval_summary.loc[:,("CHROM", "POS", "REF", "ALT", "impact", "effect", "aa_change", "gene_name", "gene_id", "corrected_spearman_cor_p")]
    interval_summary['color'] = interval_summary.impact.apply(lambda x: impact_colors[x])
    try:
        interval_summary['name'] = interval_summary.apply(lambda x: f"{x.gene_name} ({x.gene_id}) - {x.effect}\n{x.aa_change}", axis=1)
    except ValueError:
        columns = ("CHROM", "POS", "REF", "ALT", "impact", "effect", "aa_change", "gene_name", "gene_id", "corrected_spearman_cor_p")
        return jsonify(None)

    # Take top 25 most correlated genes.
    top_genes = list(interval_summary.groupby('gene_id') \
                                .corrected_spearman_cor_p \
                                .apply(lambda x: max(x)) \
                                .nlargest(25) \
                                .reset_index() \
                                .gene_id.values)

    interval_summary = interval_summary[interval_summary['gene_id'].isin(top_genes)]

    out = {k: list(interval_summary[k]) for k in interval_summary.columns.values}
    return jsonify(out)
