#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Sam Wachspress

Data Release administration

"""
import arrow

from flask import abort, flash, request, render_template, Blueprint, redirect, url_for

from base.constants import REPORT_V2_FILE_LIST, REPORT_V1_FILE_LIST, REPORT_VERSIONS
from base.config import config
from base.models import data_report_ds
from base.forms import data_report_form
from base.utils.jwt import get_jwt, admin_required, get_current_user
from base.utils.data_utils import unique_id
from base.utils.gcloud import delete_by_ref


data_admin_bp = Blueprint('data_admin',
                        __name__,
                        template_folder='admin')


cloud_config = config['cloud_config']

@data_admin_bp.route('/', methods=["GET"])
@data_admin_bp.route('/<id>', methods=["GET"])
@admin_required()
def data_admin(id=None):
  if id is None:
    title = 'All'
    items = data_report_ds().get_all()
  else:
    return redirect(url_for('data_admin.data_edit', id=id))

  return render_template('admin/data_list.html', **locals())


@data_admin_bp.route('/create/', methods=["GET"])
@admin_required()
def data_create(id=None):
  user = get_current_user()
  id = unique_id()
  report = data_report_ds(id)
  report.init()
  report.save()
  return redirect(url_for('data_admin.data_edit', id=id))


@data_admin_bp.route('/<id>/edit/', methods=["GET", "POST"])
@admin_required()
def data_edit(id=None):
  if id is None:
    flash('Error: No Report ID Provided!')
    abort(500)

  title = "Edit"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = data_report_form(request.form)

  report = data_report_ds(id)
  if not report._exists:
    flash(f"Error: Report {id} does not exist!")
    abort(500)

  # Get content of cloud bucket
  report_dirs = [''] + data_report_ds.list_bucket_dirs()
  form.dataset.choices = [(f, f) for f in report_dirs]
  form.version.choices = [(v, v) for v in REPORT_VERSIONS]

  if request.method == 'GET':
    form.dataset.data = report.dataset if hasattr(report, 'dataset') else ''
    form.wormbase.data = report.wormbase if hasattr(report, 'wormbase') else ''
    form.version.data = report.version if hasattr(report, 'version') else ''

  if request.method == 'POST' and form.validate():
    # if changes then re-sync
    report.dataset = request.form.get('dataset')
    report.wormbase = request.form.get('wormbase')
    report.version = request.form.get('version')
    report.initialized = True
    report.save()
    return redirect(url_for('data_admin.data_admin'))
  return render_template('admin/data_edit.html', **locals())


@data_admin_bp.route('/<id>/delete/', methods=["GET"])
@admin_required()
def data_delete(id=None):
  if id is None:
    flash('Error: No Report ID Provided!')
    abort(500)

  report = data_report_ds(id)
  if not report._exists:
    flash(f"Error: Report {id} does not exist!")
    abort(500)

  if hasattr(report, 'dataset'):
    dataset = str(report.dataset)
    cloud_config.create_backup()
    cloud_config.remove_release(dataset)
    cloud_config.remove_release_files(dataset)
    props = cloud_config.get_properties()
    config.update(props)
    delete_by_ref('data-report', id)

  return redirect(url_for('data_admin.data_admin'))


@data_admin_bp.route('/<id>/sync-report', methods=["GET"])
@admin_required()
def data_sync_report(id=None):
  """
    Fetches static content from a google cloud bucket and copies it locally to serve
  """
  if id is None:
    flash('Error: No Report ID Provided!')
    abort(500)

  report = data_report_ds(id)
  if not report._exists or not hasattr(report, 'dataset'):
    flash(f"Error: Report {id} does not exist!")
    abort(500)

  dataset = report.dataset if hasattr(report, 'dataset') else None
  wormbase = report.wormbase if hasattr(report, 'wormbase') else None
  version = report.version if hasattr(report, 'version') else None
  if dataset is None or wormbase is None or version is None:
    flash(f"Error: Report {id} is missing required properties!")
    abort(500)
  
  files = []
  if version == 'v1':
    files = REPORT_V1_FILE_LIST
  elif version == 'v2':
    files = REPORT_V2_FILE_LIST

  result = cloud_config.get_release_files(dataset, files, refresh=True)
  if not result is None:
    now = arrow.utcnow().datetime
    report.report_synced_on = now
    report.save()
  else:
    report.save()
    flash(f"Failed to sync report: {id}!")
    abort(500)
  
  return redirect(url_for('data_admin.data_admin'))


@data_admin_bp.route('/<id>/sync-db', methods=["GET"])
@admin_required()
def data_sync_db(id=None):
  """
    Fetches sqlite db file from google cloud bucket and copies it locally to serve
  """
  if id is None:
    flash('Error: No Report ID Provided!')
    abort(500)

  report = data_report_ds(id)
  if not report._exists or not hasattr(report, 'dataset'):
    flash(f"Error: Report {id} does not exist!")
    abort(500)

  dataset = report.dataset if hasattr(report, 'dataset') else None
  wormbase = report.wormbase if hasattr(report, 'wormbase') else None
  if dataset is None or wormbase is None:
    flash(f"Error: Report {id} is missing required properties!")
    abort(500)

  result = cloud_config.get_release_db(dataset, wormbase, refresh=True)
  if not result is None:
    now = arrow.utcnow().datetime
    report.db_synced_on = now
    report.save()
  else:
    report.save()
    flash(f"Failed to sync report: {id}!")
    abort(500)
  
  return redirect(url_for('data_admin.data_admin'))


@data_admin_bp.route('/<id>/hide', methods=["GET"])
@admin_required()
def data_hide_report(id=None):
  """ Updates the cloud config to hide the release """
  if id is None:
    flash('Error: No Report ID Provided!')
    abort(500)

  report = data_report_ds(id)
  if not report._exists or not hasattr(report, 'dataset'):
    flash(f"Error: Report {id} does not exist or is missing required properties!")
    abort(500)

  # update the config
  dataset = report.dataset
  cloud_config.create_backup()
  cloud_config.remove_release(dataset)
  props = cloud_config.get_properties()
  config.update(props)

  # update the datastore report object
  report.publish = False
  report.published_on = ''
  report.save()

  return redirect(url_for('data_admin.data_admin'))


@data_admin_bp.route('/<id>/publish', methods=["GET"])
@admin_required()
def data_publish_report(id=None):
  """ Updates the cloud config to recognize the release """
  if id is None:
    flash('Error: No Report ID Provided!')
    abort(500)

  report = data_report_ds(id)
  if not report._exists:
    flash(f"Error: Report {id} does not exist!")
    abort(500)

  dataset = report.dataset if hasattr(report, 'dataset') else None
  wormbase = report.wormbase if hasattr(report, 'wormbase') else None
  version = report.version if hasattr(report, 'version') else None
  if dataset is None or wormbase is None or version is None:
    flash(f"Error: Report {id} is missing required properties!")
    abort(500)

  cloud_config.create_backup()
  cloud_config.add_release(dataset, wormbase, version)
  props = cloud_config.get_properties()
  config.update(props)

  # update the datastore report object
  report.publish = True
  report.published_on = arrow.utcnow().datetime
  report.save()

  return redirect(url_for('data_admin.data_admin'))
