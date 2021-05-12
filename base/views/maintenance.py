import os
import time

from threading import Thread
from datetime import timedelta
from flask import jsonify, Blueprint, request, flash, abort
from logzero import logger

from base.constants import BAM_BAI_DOWNLOAD_SCRIPT_NAME
from base.config import config
from base.utils.gcloud import generate_download_signed_url_v4, upload_file
from base.views.api.api_strain import query_strains
from base.utils.cache import delete_expired_cache

maintenance_bp = Blueprint('maintenance',
                     __name__)


def verify_req_origin(request):
  cron_header = request.headers.get('X-Appengine-Cron')
  if cron_header:
    return True
  return False


@maintenance_bp.route('/cleanup_cache', methods=['GET'])
def cleanup_cache():
  if verify_req_origin(request):
    result = delete_expired_cache()
    response = jsonify({"result": result})
    response.status_code = 200
    return response
  
  flash('You do not have access to this page', 'error')
  return abort(401)

@maintenance_bp.route('/create_bam_bai_download_script', methods=['GET'])
def create_bam_bai_download_script():
  if verify_req_origin(request):
    strain_listing = query_strains(is_sequenced=True)
    joined_strain_list = ''
    for strain in strain_listing:
      joined_strain_list += strain.strain + ','
    
    thread = Thread(target=generate_bam_bai_download_script, args={joined_strain_list: joined_strain_list})
    thread.start()

    response = jsonify({})
    response.status_code = 200
    return response
  
  flash('You do not have access to this page', 'error')
  return abort(401)


def generate_bam_bai_download_script(joined_strain_list):
  ''' Generates signed downloads urls for every sequenced strain and creates a script to download them ''' 
  expiration = timedelta(days=7)
  filename = f'{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'
  blobPath = f'bam/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'

  if os.path.exists(filename):
    os.remove(filename)

  f = open(filename, "a")

  strain_listing = joined_strain_list.split(',')
  for strain in strain_listing:
    f.write(f'\n\n# Strain: {strain}')

    bam_path = 'bam/{}.bam'.format(strain)
    bam_signed_url = generate_download_signed_url_v4(bam_path, expiration=expiration)
    if bam_signed_url:
      f.write('\nwget "{}"'.format(bam_signed_url))
    
    bai_path = 'bam/{}.bam.bai'.format(strain)
    bai_signed_url = generate_download_signed_url_v4(bai_path, expiration=expiration)
    if bai_signed_url:
      f.write('\nwget "{}"'.format(bai_signed_url))

  f.close()
  upload_file(blobPath, f"{BAM_BAI_DOWNLOAD_SCRIPT_NAME}")

