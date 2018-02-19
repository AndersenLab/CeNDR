import decimal
import os
import time
import re
import arrow
import requests
import pandas as pd
import simplejson as json

from base.utils.email import send_email, MAPPING_SUBMISSION_EMAIL
from base.utils.query import get_reports_by_date
from base.constants import BIOTYPES, TABLE_COLORS
from base.application import autoconvert
from base.models2 import trait_m
from datetime import date
from dateutil.relativedelta import relativedelta
from peewee import JOIN
from flask import render_template, request, redirect, url_for, abort
from collections import OrderedDict
from slugify import slugify
from gcloud import storage
from collections import Counter
from base.forms import mapping_submission_form
from logzero import logger
from flask import session, flash, Blueprint, g
from base.utils.data_utils import unique_id
from base.constants import (REPORT_VERSION,
                            DATASET_RELEASE,
                            CENDR_VERSION,
                            WORMBASE_VERSION)

from base.utils.gcloud import query_item

from base.utils.plots import pxg_plot, plotly_distplot


mapping_bp = Blueprint('mapping',
                       __name__,
                       template_folder='mapping')


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, date):
            return str(o)
        return super(CustomEncoder, self).default(o)


@mapping_bp.route('/mapping/perform-mapping/', methods=['GET', 'POST'])
def mapping():
    """
        This is the mapping submission page.
    """
    form = mapping_submission_form(request.form)

    VARS = {'title': 'Perform Mapping',
            'form': form}

    user = session.get('user')
    if form.validate_on_submit() and user:
        form.data.pop("csrf_token")
        report_slug = slugify(form.report_name.data)
        trait_list = list(form.trait_data.processed_data.columns[2:])
        strain_list = form.trait_data.strain_list
        is_public = form.is_public.data
        trait_data = form.trait_data.processed_data.to_csv(index=False, sep="\t", na_rep="NA")
        report_name = form.report_name.data
        report_data = {'report_slug': slugify(form.report_name.data),
                       'report_name': report_name,
                       'description': form.description.data,
                       'trait_data': trait_data,
                       'created_on': arrow.utcnow().datetime,
                       'username': user['username'],
                       'user_id': user['user_id'],
                       'user_email': user['user_email'],
                       'is_public': is_public,
                       'trait_list': trait_list,
                       'strain_list': strain_list}
        if is_public is False:
            report_data['secret_hash'] = unique_id()[0:8]
        report_data = {k: v for k, v in report_data.items() if v}
        # Begin a transaction so nothing is saved unless the tasks start
        # running.
        transaction = g.ds.transaction()
        transaction.begin()

        # Now generate and run trait tasks
        for trait_name in report.trait_list:
            trait = trait_m()
            trait.__dict__.update(report_data)
            trait.__dict__.update({
               'report_name': report_name,
               'report_slug': report_slug,
               'trait_name': trait_name,
               'created_on': arrow.utcnow().datetime,
               'status': 'Queued',
               'CENDR_VERSION': CENDR_VERSION,
               'REPORT_VERSION': REPORT_VERSION,
               'DATASET_RELEASE': DATASET_RELEASE,
               'WORMBASE_VERSION': WORMBASE_VERSION
            })
            trait.run_task()
        # Update the report to contain the set of the
        # latest task runs
        transaction.commit()

        flash("Successfully submitted mapping!", 'success')
        return redirect(url_for('mapping.report',
                                report_slug=report_slug,
                                trait_name=trait_list[0]))

    return render_template('mapping.html', **VARS)


@mapping_bp.route("/report/<report_slug>/")
@mapping_bp.route("/report/<report_slug>/<trait_name>")
@mapping_bp.route("/report/<report_slug>/<trait_name>/<rerun>")
def report(report_slug, trait_name=None, rerun=None):
    """
        This view will handle logic of handling legacy reports
        and v2 reports.

    """
    trait_set = query_item('trait', filters=[('report_slug', '=', report_slug)])

    # Get first report
    try:
        trait = trait_set[0]
    except IndexError:
        try:
            trait_set = query_item('trait', filters=[('secret_hash', '=', report_slug)])
            trait = trait_set[0]
        except IndexError:
            flash('Cannot find report', 'danger')
            return abort(404)

    # Verify user has permission to view report
    user = session.get('user')
    if not trait['is_public']:
        if user:
            user_id = user.get('user_id')
        else:
            user_id = None
        if trait['secret_hash'] != report_slug and user_id != trait['user_id']:
            flash('You do not have access to that report', 'danger')
            return abort(404)

    if not trait_name:
        # Redirect to the first trait
        return redirect(url_for('mapping.report',
                                report_slug=report_slug,
                                trait_name=trait['trait_list'][0]))

    try:
        # Resolve REPORT --> TRAIT
        # Fetch trait and convert to trait object.
        cur_trait = [x for x in trait_set if x['trait_name'] == trait_name][0]
        trait = trait_m(cur_trait.key.name)
        trait.__dict__.update(cur_trait)
    except IndexError:
        return abort(404)

    VARS = {
        'title': trait.report_name,
        'subtitle': trait_name,
        'trait_name': trait_name,
        'report_slug': report_slug,
        'trait': trait,
        'trait_set': trait_set,
        'BIOTYPES': BIOTYPES,
        'TABLE_COLORS': TABLE_COLORS
    }
    if trait.status == 'complete':
        if trait.REPORT_VERSION == 'v1':
            """
                VERSION 1
            """
            phenotype_data = trait.get_gs_as_dataset("tables/phenotype.tsv")
            isotypes = list(phenotype_data.iloc[:, 1].dropna().values)
            phenotype_data = list(phenotype_data.iloc[:, 3].values)
            VARS.update({'phenotype_data': phenotype_data,
                         'isotypes': isotypes})
            if trait.is_significant:
                interval_summary = trait.get_gs_as_dataset("tables/interval_summary.tsv.gz") \
                                        .rename(index=str, columns={'gene_w_variants': 'genes w/ variants'})
                variant_correlation = trait.get_gs_as_dataset("tables/variant_correlation.tsv.gz")
                max_corr = variant_correlation.groupby(['gene_id', 'interval']).apply(lambda x: max(abs(x.correlation)))
                max_corr = max_corr.reset_index().rename(index=str, columns={0: 'max_correlation'})
                variant_correlation = pd.merge(variant_correlation, max_corr, on=['gene_id', 'interval']) \
                                        .sort_values(['max_correlation', 'gene_id'], ascending=False)
                peak_summary = trait.get_gs_as_dataset("tables/peak_summary.tsv.gz")
                peak_summary['interval'] = peak_summary.apply(lambda row: f"{row.chrom}:{row.interval_start}-{row.interval_end}", axis=1)
                first_peak = peak_summary.iloc[0]
                VARS.update({'peak_summary': peak_summary,
                             'first_peak': first_peak,
                             'n_peaks': len(peak_summary),
                             'variant_correlation': variant_correlation,
                             'interval_summary': interval_summary})
        elif trait.REPORT_VERSION == 'v2':
            """
                VERSION 2
            """
            # If the mapping is complete:
            # Phenotype plot
            phenotype_plot = plotly_distplot(report._trait_df, trait_name)
            # Fetch datafiles for complete runs
            peak_summary = trait.get_gs_as_dataset("peak_summary.tsv.gz")
            try:
                first_peak = peak_summary.iloc[0]
                chrom, start, end = re.split(":|\-", first_peak.interval)
                first_peak['chrom'] = chrom
                first_peak['pos'] = int(first_peak['peak_pos'].split(":")[1])
                first_peak['start'] = start
                first_peak['end'] = end
            except:
                first_peak = None

            interval_summary = trait.get_gs_as_dataset("interval_summary.tsv.gz") \
                                    .rename(index=str, columns={'gene_w_variants': 'genes w/ variants'})

            peak_marker_data = trait.get_gs_as_dataset("peak_markers.tsv")
            peak_summary = trait.get_gs_as_dataset("peak_summary.tsv.gz")
            VARS.update({'pxg_plot': pxg_plot(peak_marker_data, trait_name),
                         'interval_summary': interval_summary,
                         'variant_correlation': trait.get_gs_as_dataset("interval_variants.tsv.gz"),
                         'peak_summary': peak_summary,
                         'phenotype_plot': phenotype_plot,
                         'n_peaks': len(peak_summary),
                         'strain_count': report.trait_strain_count(trait_name),
                         'isotypes': list(report._trait_df.ISOTYPE.values),
                         'first_peak': first_peak})

            # To handle report data, functions specific
            # to the version will be required.
    
    report_template = f"reports/{trait.REPORT_VERSION}.html"
    return render_template(report_template, **VARS)


@mapping_bp.route('/mapping/public/', methods=['GET'])
def public_mapping():
    query = request.args.get("query")
    if query is not None:
        title = "Search: " + query
        subtitle = "results"
        q = "%" + query + "%"
        results = trait.select(report, trait, mapping).filter(trait.status == "complete", report.release == 0).join(mapping).join(report).dicts().filter((trait.trait_name % q) |
                                    (trait.trait_name % q) |
                                    (report.report_name % q) |
                                    (report.report_slug % q)).order_by(mapping.log10p.desc())
        search_results = list(results.dicts().execute())
        search = True
        return render_template('public_mapping.html', **locals())
    title = "Perform Mapping"
    waffle_date_set = get_reports_by_date().to_dict('records')

    VARS = {'waffle_data_set': waffle_date_set}

    pub_mappings = query_item('mapping', filters=[('is_public', '=', True)])
    return render_template('public_mapping.html', **locals())




