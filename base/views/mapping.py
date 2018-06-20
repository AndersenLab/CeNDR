import decimal
import re
import arrow
import urllib
import pandas as pd
import simplejson as json

from base.constants import BIOTYPES, TABLE_COLORS
from base.models2 import trait_m
from datetime import date
from dateutil.relativedelta import relativedelta
from flask import render_template, request, redirect, url_for, abort
from slugify import slugify
from base.forms import mapping_submission_form
from logzero import logger
from flask import session, flash, Blueprint, g
from base.utils.data_utils import unique_id
from base.constants import (REPORT_VERSION,
                            DATASET_RELEASE,
                            CENDR_VERSION,
                            WORMBASE_VERSION)

from base.utils.gcloud import query_item, get_item, delete_item

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
        transaction = g.ds.transaction()
        transaction.begin()

        # Now generate and run trait tasks
        report_name = form.report_name.data
        report_slug = slugify(report_name)
        trait_list = list(form.trait_data.processed_data.columns[2:])
        now = arrow.utcnow().datetime
        trait_set = []
        secret_hash = unique_id()[0:8]
        for trait_name in trait_list:
            trait = trait_m()
            trait_data = form.trait_data.processed_data[['ISOTYPE', 'STRAIN', trait_name]].dropna(how='any') \
                                                                                          .to_csv(index=False,
                                                                                                  sep="\t",
                                                                                                  na_rep="NA")
            trait.__dict__.update({
               'report_name': report_name,
               'report_slug': report_slug,
               'trait_name': trait_name,
               'trait_list': list(form.trait_data.processed_data.columns[2:]),
               'trait_data': trait_data,
               'n_strains': int(form.trait_data.processed_data.STRAIN.count()),
               'created_on': now,
               'status': 'queued',
               'is_public': form.is_public.data == 'true',
               'CENDR_VERSION': CENDR_VERSION,
               'REPORT_VERSION': REPORT_VERSION,
               'DATASET_RELEASE': DATASET_RELEASE,
               'WORMBASE_VERSION': WORMBASE_VERSION,
               'username': user['username'],
               'user_id': user['user_id'],
               'user_email': user['user_email']
            })
            if trait.is_public is False:
                trait.secret_hash = secret_hash
            trait.run_task()
            trait_set.append(trait)
        # Update the report to contain the set of the
        # latest task runs
        transaction.commit()

        flash("Successfully submitted mapping!", 'success')
        return redirect(url_for('mapping.report_view',
                                report_slug=report_slug,
                                trait_name=trait_list[0]))

    return render_template('mapping.html', **VARS)


@mapping_bp.route("/report/<report_slug>/")
@mapping_bp.route("/report/<report_slug>/<trait_name>")
@mapping_bp.route("/report/<report_slug>/<trait_name>/<rerun>")
def report_view(report_slug, trait_name=None, rerun=None):
    """
        This view will handle logic of handling legacy reports
        and v2 reports.

    """

    # Enable reruns
    if rerun:
        trait_set = query_item('trait', filters=[('report_slug', '=', report_slug), ('trait_name', '=', trait_name)])
        for n, existing_trait in enumerate(trait_set):
            logger.info(n)
            logger.info(existing_trait.key)
            delete_item(existing_trait)
        trait = trait_m(trait_set[0])

        mapping_items = query_item('mapping', filters=[('report_slug', '=', report_slug), ('trait_slug', '=', trait_name)])
        for existing_mapping in mapping_items:
            delete_item(existing_mapping)

        trait.status = "Rerunning"
        # Running the task will save it.
        trait.run_task()
        return redirect(url_for('mapping.report_view',
                                report_slug=report_slug,
                                trait_name=trait_name))

    trait_set = query_item('trait', filters=[('report_slug', '=', report_slug)])

    # Get first report if available.
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
    if not trait.get('is_public'):
        if user:
            user_id = user.get('user_id')
        else:
            user_id = None
        if trait['secret_hash'] != report_slug and user_id != trait['user_id']:
            flash('You do not have access to that report', 'danger')
            return abort(404)

    if not trait_name:
        logger.error("Trait name not found")
        # Redirect to the first trait
        return redirect(url_for('mapping.report_view',
                                report_slug=report_slug,
                                trait_name=trait_set[0]['trait_name']))

    try:
        # Resolve REPORT --> TRAIT
        # Fetch trait and convert to trait object.
        cur_trait = [x for x in trait_set if x['trait_name'] == trait_name][0]
        trait = trait_m(cur_trait.key.name)
        trait.__dict__.update(cur_trait)
        logger.info(trait)
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
        'TABLE_COLORS': TABLE_COLORS,
        'n_peaks': 0
    }

    # Set status to error if the container is stopped and status is not set to complete.
    if trait.container_status() == 'STOPPED' and trait.status != "complete":
        trait.status = 'error'
        trait.save()

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
                try:
                    variant_correlation = trait.get_gs_as_dataset("tables/variant_correlation.tsv.gz")
                    max_corr = variant_correlation.groupby(['gene_id', 'interval']).apply(lambda x: max(abs(x.correlation)))
                    max_corr = max_corr.reset_index().rename(index=str, columns={0: 'max_correlation'})
                    variant_correlation = pd.merge(variant_correlation, max_corr, on=['gene_id', 'interval']) \
                                            .sort_values(['max_correlation', 'gene_id'], ascending=False)
                except urllib.error.HTTPError:
                    variant_correlation = []
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

            phenotype_plot = plotly_distplot(trait._trait_df, trait_name)
            VARS.update({'phenotype_plot': phenotype_plot})
            # Fetch datafiles for complete runs
            VARS.update({'n_peaks': 0})
            if trait.is_significant:
                peak_summary = trait.get_gs_as_dataset("peak_summary.tsv.gz")
                try:
                    first_peak = peak_summary.loc[0]
                    chrom, interval_start, interval_end = re.split(":|\-", first_peak['interval'])
                    first_peak.chrom = chrom
                    first_peak.pos = int(first_peak['peak_pos'].split(":")[1])
                    first_peak.interval_start = int(interval_start)
                    first_peak.interval_end = int(interval_end)
                except:
                    first_peak = None

                interval_summary = trait.get_gs_as_dataset("interval_summary.tsv.gz") \
                                        .rename(index=str, columns={'gene_w_variants': 'genes w/ variants'})

                peak_marker_data = trait.get_gs_as_dataset("peak_markers.tsv.gz")
                peak_summary = trait.get_gs_as_dataset("peak_summary.tsv.gz")
                VARS.update({'pxg_plot': pxg_plot(peak_marker_data, trait_name),
                             'interval_summary': interval_summary,
                             'variant_correlation': trait.get_gs_as_dataset("interval_variants.tsv.gz"),
                             'peak_summary': peak_summary,
                             'n_peaks': len(peak_summary),
                             'isotypes': list(trait._trait_df.ISOTYPE.values),
                             'first_peak': first_peak})

            # To handle report data, functions specific
            # to the version will be required.
    
    report_template = f"reports/{trait.REPORT_VERSION}.html"
    return render_template(report_template, **VARS)


@mapping_bp.route('/mapping/public/', methods=['GET'])
def public_mapping():
    query = request.args.get("query")
    title = "Public Mappings"
    pub_mappings = query_item('mapping', filters=[('is_public', '=', True)])
    return render_template('public_mapping.html', **locals())




