from threading import Thread
from base.utils.gcloud import generate_download_signed_url_v4
import os
import time

from datetime import timedelta
from flask import jsonify, Blueprint

from base.config import config
from base.constants import BAM_BAI_DOWNLOAD_SCRIPT_NAME
from base.views.api.api_strain import query_strains
from base.utils.cache import delete_expired_cache

maintenance_bp = Blueprint('maintenance',
                     __name__)


@maintenance_bp.route('/cleanup_cache', methods=['GET'])
def cleanup_cache():
  result = delete_expired_cache()
  response = jsonify({"result": result})
  response.status_code = 200
  return response

@maintenance_bp.route('/create_bam_bai_download_script', methods=['GET'])
def create_bam_bai_download_script():
  strain_listing = query_strains(release=config["DATASET_RELEASE"], is_sequenced=True)
  joined_strain_list = ''
  for strain in strain_listing:
    joined_strain_list += strain.strain + ','
  
  thread = Thread(target=generate_bam_bai_download_script, args={joined_strain_list: joined_strain_list})
  thread.start()

  response = jsonify({})
  response.status_code = 200
  return response


def generate_bam_bai_download_script(joined_strain_list):
  ''' Generates signed downloads urls for every sequenced strain and creates a script to download them ''' 
  expiration = timedelta(days=7)
  filename = f'base/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}'

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
