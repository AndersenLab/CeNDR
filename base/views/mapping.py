import decimal
import re
import csv
import urllib
import pandas as pd
import simplejson as json
import os

from datetime import date
from flask import render_template, request, redirect, url_for, abort
from slugify import slugify
from logzero import logger
from flask import session, flash, Blueprint, g


from base.constants import BIOTYPES, GOOGLE_CLOUD_BUCKET, TABLE_COLORS
from base.config import config
from base.models import trait_ds, ns_calc_ds
from base.forms import file_upload_form
from base.utils.data_utils import unique_id, hash_file_upload
from base.utils.gcloud import check_blob, list_files, query_item, delete_item, upload_file, add_task
from base.utils.jwt_utils import jwt_required, get_jwt, get_current_user
from base.utils.plots import pxg_plot, plotly_distplot


mapping_bp = Blueprint('mapping',
                       __name__,
                       template_folder='mapping')


# Create a directory in a known location to save files to.
uploads_dir = os.path.join('./', 'uploads')
os.makedirs(uploads_dir, exist_ok=True)

class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, date):
            return str(o)
        return super(CustomEncoder, self).default(o)

def create_ns_task(data_hash, ds_id, ds_kind):
  """
      Creates a Cloud Task to schedule the pipeline for execution
      by the NemaScan service
  """
  ns = ns_calc_ds(ds_id)

  # schedule nemascan request
  queue = config['NEMASCAN_PIPELINE_TASK_QUEUE']
  url = config['NEMASCAN_PIPELINE_URL']
  data = {'hash': data_hash, 'ds_id': ds_id, 'ds_kind': ds_kind}
  result = add_task(queue, url, data, task_name=data_hash)

  # Update report status
  ns.status = 'SCHEDULED' if result else 'FAILED'
  ns.save()


@mapping_bp.route('/mapping/upload', methods = ['POST'])
@jwt_required()
def schedule_mapping():
  '''
    Uploads the users file and schedules the nemascan pipeline task
    tracking metadata in an associated datastore entry
  '''
  form = file_upload_form(request.form)
  if not form.validate_on_submit():
    flash("You must include a description of your data and a TSV file to upload", "error")
    return redirect(url_for('mapping.mapping'))

  # Store report metadata in datastore
  user = get_current_user()
  id = unique_id()
  ns = ns_calc_ds(id)
  ns.label = request.form.get('label')
  ns.username = user.name
  ns.status = 'NEW'
  ns.save()

  # Upload file to cloud bucket
  file = request.files['file']
  local_path = os.path.join(uploads_dir, f'{id}.tsv')
  file.save(local_path)

  # Read trait from file (also verify first row)
  with open(local_path, 'r') as f:
    csv_reader = csv.reader(f, delimiter='\t')
    csv_headings = next(csv_reader)
  if csv_headings[0] != 'strain' or len(csv_headings) != 2 or len(csv_headings[1]) == 0:
    flash("Please make sure that your data file exactly matches the sample format")
    return redirect(url_for('mapping.mapping'))

  trait = csv_headings[1]
  data_hash = hash_file_upload(local_path, length=32)

  # Update report status
  ns.data_hash = data_hash
  ns.trait = trait
  ns.status = 'RECEIVED'
  ns.save()

  # Check if the file already exists in google storage (matching hash)
  data_blob = f"reports/nemascan/{data_hash}/data.tsv"
  data_exists = list_files(data_blob)
  # if there is anything in the results directory, don't schedule the task
  # (could be running, failed, etc.. need to check result directory in more detail to confirm state)
  if len(data_exists) > 0:
    flash('It looks like that data has already been uploaded - You will be redirected to the saved results', 'danger')
    return redirect(url_for('mapping.mapping_report', id=id))

  # Upload file to google storage
  result = upload_file(data_blob, local_path)
  if not result:
    ns.status = 'ERROR UPLOADING'
    ns.save()
    flash("There was an error uploading your data")
    return redirect(url_for('mapping.mapping'))

  # Schedule task
  create_ns_task(data_hash, id, ns.kind)
    
  # Delete copy stored locally on server
  os.remove(local_path) 

  return redirect(url_for('mapping.mapping_report', id=id))


@mapping_bp.route('/mapping/report/all', methods=['GET', 'POST'])
@jwt_required()
def mapping_result_list():
  title = 'Genetic Mapping'
  subtitle = 'Report List'
  user = get_current_user()
  items = ns_calc_ds().query_by_username(user.name)
  items = sorted(items, key=lambda x: x['created_on'], reverse=True)
  return render_template('mapping_result_list.html', **locals())


@mapping_bp.route('/mapping/report/<id>/', methods=['GET'])
@jwt_required()
def mapping_report(id):
  title = 'Genetic Mapping'
  user = get_current_user()
  ns = ns_calc_ds(id)
  fluid_container = True
  subtitle = ns.label +': ' + ns.trait

  # check if DS entry has complete status
  data_hash = ns.data_hash
  if (ns.status == 'COMPLETE' and len(ns.report_path) > 0):
    report_path = ns.report_path
    result = True
  else:
    # check if there is a report on GS, just to be sure
    data_blob = f"reports/nemascan/{data_hash}/results/Reports/NemaScan_Report_"
    result = list_files(data_blob)
    if len(result) > 0:
      for x in result:
        if x.name.endswith('.html'):
          # Store report URL in DS
          report_path = GOOGLE_CLOUD_BUCKET + '/' + x.name
          ns.report_path = report_path
          ns.status = 'COMPLETE'
          result = True
          ns.save()

  return render_template('mapping_result.html', **locals())


@mapping_bp.route('/mapping/results/<id>/', methods=['GET'])
@jwt_required()
def mapping_results(id):
  title = 'Genetic Mapping'
  subtitle = 'Result Files'
  user = get_current_user()
  ns = ns_calc_ds(id)
  
  data_blob = f"reports/nemascan/{ns.data_hash}/results/"
  blobs = list_files(data_blob)
  file_list = []
  for blob in blobs:
    file_list.append({
      "name": blob.name.rsplit('/', 2)[1] + '/' + blob.name.rsplit('/', 2)[2],
      "url": blob.public_url
    })
  return render_template('mapping_result_files.html', **locals())


@mapping_bp.route('/mapping/perform-mapping/', methods=['GET', 'POST'])
@jwt_required()
def mapping():
  """
      This is the mapping submission page.
  """
  title = 'Perform Mapping'
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = file_upload_form()

  return render_template('mapping.html', **locals())


@mapping_bp.route("/report/<report_slug>/")
@mapping_bp.route("/report/<report_slug>/<trait_name>")
@mapping_bp.route("/report/<report_slug>/<trait_name>/<rerun>")
def report_view(report_slug, trait_name=None, rerun=None):
    """
        This view will handle logic of handling legacy reports
        and v2 reports.

    """

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

    # Enable reruns
    if rerun:
        trait_set = [x for x in trait_set if x['trait_name'] == trait_name]
        for n, existing_trait in enumerate(trait_set):
            logger.info(n)
            logger.info(existing_trait.key)
            delete_item(existing_trait)
        trait = trait_ds(trait_set[0])

        mapping_items = query_item('mapping', filters=[('report_slug', '=', report_slug), ('trait_slug', '=', trait_name)])
        for existing_mapping in mapping_items:
            delete_item(existing_mapping)

        trait.status = "Rerunning"
        # Running the task will save it.
        trait.run_task()
        return redirect(url_for('mapping.report_view',
                                report_slug=report_slug,
                                trait_name=trait_name))

    # Verify user has permission to view report
    # todo: replace session user id and props with datastore user and props
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
        trait = trait_ds(cur_trait.key.name)
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
                except (urllib.error.HTTPError, pd.errors.EmptyDataError):
                    variant_correlation = []
                peak_summary = trait.get_gs_as_dataset("tables/peak_summary.tsv.gz")
                peak_summary['interval'] = peak_summary.apply(lambda row: f"{row.chrom}:{row.interval_start}-{row.interval_end}", axis=1)
                first_peak = peak_summary.iloc[0]
                VARS.update({'peak_summary': peak_summary,
                             'first_peak': first_peak,
                             'n_peaks': len(peak_summary),
                             'variant_correlation': variant_correlation,
                             'interval_summary': interval_summary})

        elif trait.REPORT_VERSION == "v2":
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

                try:
                    variant_correlation = trait.get_gs_as_dataset("interval_variants.tsv.gz")
                except (pd.errors.EmptyDataError):
                    variant_correlation = pd.DataFrame()

                interval_summary = trait.get_gs_as_dataset("interval_summary.tsv.gz") \
                                        .rename(index=str, columns={'gene_w_variants': 'genes w/ variants'})

                peak_marker_data = trait.get_gs_as_dataset("peak_markers.tsv.gz")
                peak_summary = trait.get_gs_as_dataset("peak_summary.tsv.gz")
                VARS.update({'pxg_plot': pxg_plot(peak_marker_data, trait_name),
                             'interval_summary': interval_summary,
                             'variant_correlation': variant_correlation,
                             'peak_summary': peak_summary,
                             'n_peaks': len(peak_summary),
                             'isotypes': list(trait._trait_df.ISOTYPE.values),
                             'first_peak': first_peak})

            # To handle report data, functions specific
            # to the version will be required.

    report_template = f"reports/{trait.REPORT_VERSION}.html"
    return render_template(report_template, **VARS)

