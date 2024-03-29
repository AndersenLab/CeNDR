import decimal
import csv
import simplejson as json
import os

from datetime import date
from flask import render_template, request, redirect, url_for, abort
from logzero import logger
from flask import session, flash, Blueprint, g


from base.constants import GOOGLE_CLOUD_BUCKET
from base.config import config
from base.models import ns_calc_ds, gls_op_ds
from base.forms import file_upload_form
from base.utils.data_utils import unique_id, hash_file_contents
from base.utils.gcloud import list_files, upload_file, add_task
from base.utils.jwt_utils import jwt_required, get_jwt, get_current_user


mapping_bp = Blueprint('mapping',
                       __name__,
                       template_folder='mapping')

DATA_BLOB_PATH = 'reports/nemascan/{data_hash}/data.tsv'
REPORT_BLOB_PATH = 'reports/nemascan/{data_hash}/results/Reports/NemaScan_Report_'
RESULT_BLOB_PATH = 'reports/nemascan/{data_hash}/results/'


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
  result = add_task(queue, url, data, task_name=ds_id)

  # Update report status
  if result:
    ns.status = 'SCHEDULED'
  else:
    ns.status = 'FAILED'
    
  return result


def is_data_cached(data_hash):
  # Check if the file already exists in google storage (matching hash)
  data_blob = DATA_BLOB_PATH.format(data_hash=data_hash)
  data_exists = list_files(data_blob)
  if len(data_exists) > 0:
    return True
  return False

def is_result_cached(ns):
  if ns.status == 'COMPLETE' and len(ns.report_path) > 0:
    return True

  # Check the datastore entry for the GLS pipeline execution
  glsOp = gls_op_ds(ns.data_hash)
  if hasattr(glsOp, 'error'):
    ns.status = 'ERROR'
    ns.save()
    return False
  
  # check if there is a report on GS, just to be sure
  data_blob = REPORT_BLOB_PATH.format(data_hash=ns.data_hash)    
  result = list_files(data_blob)
  if len(result) > 0:
    for x in result:
      if x.name.endswith('.html'):
        report_path = GOOGLE_CLOUD_BUCKET + '/' + x.name
        ns.report_path = report_path
        ns.status = 'COMPLETE'
        ns.save()
        return True
  else:
    if hasattr(glsOp, 'done'):
      ns.status = 'DONE'
      ns.save()
    return False

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

  # Save uploaded file to server temporarily
  file = request.files['file']
  local_path = os.path.join(uploads_dir, f'{id}.tsv')
  file.save(local_path)

  # Read first line from tsv
  with open(local_path, 'r') as f:
    csv_reader = csv.reader(f, delimiter='\t')
    csv_headings = next(csv_reader)

  # Check first line for column headers (strain, {TRAIT})
  if csv_headings[0] != 'strain' or len(csv_headings) != 2 or len(csv_headings[1]) == 0:
    os.remove(local_path)
    flash("Please make sure that your data file exactly matches the sample format", 'error')
    return redirect(url_for('mapping.mapping'))

  trait = csv_headings[1]
  data_hash = hash_file_contents(local_path, length=32)

  # Update report status
  ns.data_hash = data_hash
  ns.trait = trait
  ns.status = 'RECEIVED'
  ns.save()

  if is_data_cached(data_hash):
    flash('It looks like that data has already been uploaded - You will be redirected to the saved results', 'danger')
    return redirect(url_for('mapping.mapping_report', id=id))

  # Upload file to google storage
  data_blob = DATA_BLOB_PATH.format(data_hash=data_hash)
  result = upload_file(data_blob, local_path)
  if not result:
    ns.status = 'ERROR UPLOADING'
    ns.save()
    flash("There was an error uploading your data")
    return redirect(url_for('mapping.mapping'))

  # Schedule task
  task_result = create_ns_task(data_hash, id, ns.kind)
    
  # Delete copy stored locally on server
  os.remove(local_path) 

  if not task_result: 
    flash("There was an error scheduling your calculations...")
    redirect(url_for('mapping.mapping'))

  return redirect(url_for('mapping.mapping_report', id=id))


@mapping_bp.route('/mapping/report/all', methods=['GET', 'POST'])
@jwt_required()
def mapping_result_list():
  title = 'Genetic Mapping'
  subtitle = 'Report List'
  user = get_current_user()
  items = ns_calc_ds().query_by_username(user.name)
  # check for status changes
  for x in items:
    x = ns_calc_ds(x)
    prevStatus = x.status
    if prevStatus != 'COMPLETE' and prevStatus != 'ERROR' and prevStatus != 'DONE':
      is_result_cached(x)

  items = sorted(items, key=lambda x: x['created_on'], reverse=True)
  return render_template('mapping_result_list.html', **locals())


@mapping_bp.route('/mapping/report/<id>/', methods=['GET'])
@jwt_required()
def mapping_report(id):
  title = 'Genetic Mapping Report'
  user = get_current_user()
  ns = ns_calc_ds(id)
  fluid_container = True
  subtitle = ns.label +': ' + ns.trait
  # check if DS entry has complete status
  result = is_result_cached(ns)
  if result:
    report_path = ns.report_path
  
  return render_template('mapping_result.html', **locals())


@mapping_bp.route('/mapping/results/<id>/', methods=['GET'])
@jwt_required()
def mapping_results(id):
  title = 'Genetic Mapping Results'
  user = get_current_user()
  ns = ns_calc_ds(id)
  result = is_result_cached(ns)
  subtitle = ns.label + ': ' + ns.trait

  data_blob = RESULT_BLOB_PATH.format(data_hash=ns.data_hash)
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

