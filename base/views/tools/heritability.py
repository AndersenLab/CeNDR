import io
import pandas as pd
import json

from flask import (flash,
                   request,
                   redirect,
                   url_for,
                   jsonify,
                   render_template,
                   Blueprint,
                   abort)
from logzero import logger
from datetime import datetime

from base.config import config
from base.views.api.api_strain import get_strains
from base.utils.data_utils import hash_it, unique_id
from base.utils.jwt_utils import jwt_required, get_jwt, get_current_user
from base.utils.gcloud import check_blob, upload_file, add_task
from base.forms import heritability_form
from base.models import h2calc_ds

# ================== #
#   heritability     #
# ================== #

# Tools blueprint
heritability_bp = Blueprint('heritability',
                            __name__,
                            template_folder='tools')


def create_h2_task(data_hash, ds_id, ds_kind):
  """
      This is designed to be run in the background on the server.
      It will run a heritability analysis on google cloud run
  """
  hr = h2calc_ds(ds_id)

  # Perform h2 request
  queue = config['HERITABILITY_CALC_TASK_QUEUE']
  url = config['HERITABILITY_CALC_URL']
  data = {'hash': data_hash, 'ds_id': ds_id, 'ds_kind': ds_kind}
  result = add_task(queue, url, data, task_name=data_hash)

  # Update report status
  hr.status = 'SCHEDULED' if result else 'FAILED'
  hr.save()


@heritability_bp.route('/heritability')
def heritability():
  title = "Heritability Calculator"
  form = heritability_form()
  hide_form = True
  strain_list = []
  return render_template('tools/heritability_calculator.html', **locals())


@heritability_bp.route('/heritability/create', methods=["GET"])
@jwt_required()
def heritability_create():
  """
      This endpoint is used to create a heritability job.
  """
  title = "Heritability Calculator"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = heritability_form()
  strain_data = get_strains()
  strain_list = []
  for x in strain_data:
    strain_list.append(x.strain)

  hide_form = False
  id = unique_id()
  return render_template('tools/heritability_calculator.html', **locals())
  

@heritability_bp.route('/heritability/submit', methods=["POST"])
@jwt_required()
def submit_h2():
  """
      This endpoint is used to submit a heritability job.
      The endpoint request is executed as a background task to keep the job alive.
  """
  user = get_current_user()
  label = request.values['label']

  # Process data into tsv
  data = json.loads(request.values['table_data'])
  data = [x for x in data[1:] if x[0] is not None]
  header = ["AssayNumber", "Strain", "TraitName", "Replicate", "Value"]
  data = pd.DataFrame(data, columns=header)
  trait = data.values[0][2]
  data = data.to_csv(index=False, sep="\t")
  
  # Generate an ID for the data based on its hash
  data_hash = hash_it(data, length=32)
  logger.debug(data_hash)

  # Store the report info for user in datastore
  id = unique_id()
  hr = h2calc_ds(id)
  hr.label = label
  hr.data_hash = data_hash
  hr.username = user.name
  hr.status = 'NEW'
  hr.trait = trait
  hr.save()

  # Check whether analysis has previously been run and if so - skip
  result = check_blob(f"reports/heritability/{data_hash}/result.tsv")
  if result:
    hr.status = 'COMPLETE'
    hr.save()
    return jsonify({'thread_name': 'done',
                    'started': True,
                    'data_hash': data_hash,
                    'id': id})

  # Upload data immediately.
  data_blob = f"reports/heritability/{data_hash}/data.tsv"
  upload_file(data_blob, data, as_string=True)
  hr.status = 'RECEIVED'
  hr.save()

  # Schedule the task
  create_h2_task(data_hash, id, hr.kind)
  return jsonify({'started': True,
                  'data_hash': data_hash,
                  'id': id})


@heritability_bp.route("/heritability/h2/<id>")
@jwt_required()
def heritability_result(id):
  title = "Heritability Results"
  user = get_current_user()
  hr = h2calc_ds(id)
  ready = False

  if (not hr._exists) or (hr.username != user.name):
    flash('You do not have access to that report', 'danger')
    abort(401)

  data_hash = hr.data_hash
  data = check_blob(f"reports/heritability/{data_hash}/data.tsv")
  result = check_blob(f"reports/heritability/{data_hash}/result.tsv")

  if data is None:
    hr.status = 'NOT FOUND'
    hr.save()
    return abort(404, description="Heritability report not found")
  data = data.download_as_string().decode('utf-8')
  data = pd.read_csv(io.StringIO(data), sep="\t")
  data['AssayNumber'] = data['AssayNumber'].astype(str)
  data['label'] = data.apply(lambda x: f"{x['AssayNumber']}: {x['Value']}", 1)
  data = data.to_dict('records')
  trait = data[0]['TraitName']
  # Get trait and set title
  title = f"Heritability Results: {trait}"

  if result:
    hr.status = 'COMPLETE'
    hr.save()
    result = result.download_as_string().decode('utf-8')
    result = pd.read_csv(io.StringIO(result), sep="\t")
    result = result.to_dict('records')[0]

    fnam=datetime.today().strftime('%Y%m%d.')+trait
    ready = True

  return render_template("tools/heritability_results.html", **locals())


@heritability_bp.route("/heritability/h2/all")
@jwt_required()
def heritability_result_list():
  title = "Heritability Results"
  user = get_current_user()
  items = h2calc_ds().query_by_username(user.name)
  items = sorted(items, key=lambda x: x['created_on'], reverse=True)
  for x in items:
    data_hash = x['data_hash']
    if check_blob(f"reports/heritability/{data_hash}/result.tsv"):
      x.status = 'COMPLETE'
  return render_template('tools/h2_result_list.html', **locals())
