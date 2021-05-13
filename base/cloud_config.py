# Application Cloud Configuration for Site Static Content hosted externally
import os
import shutil
import json

from os import path
from logzero import logger
from google.oauth2 import service_account
from google.cloud import datastore, storage

from base.constants import REPORT_V1_FILE_LIST, REPORT_V2_FILE_LIST, GOOGLE_CLOUD_BUCKET
from base.utils.data_utils import dump_json, unique_id

class CloudConfig:

  ds_client = None
  storage_client = None
  kind = 'cloud-config'
  default_cc = { 'releases' : [{'dataset': '20210121', 'wormbase': 'WS276', 'version': 'v2'},
                              {'dataset': '20200815', 'wormbase': 'WS276', 'version': 'v2'},
                              {'dataset': '20180527', 'wormbase': 'WS263', 'version': 'v1'},
                              {'dataset': '20170531', 'wormbase': 'WS258', 'version': 'v1'},
                              {'dataset': '20160408', 'wormbase': 'WS245', 'version': 'v1'}] }

  def __init__(self, name, cc=default_cc, kind_prefix='', local=True):
    self.kind = '{}{}'.format(kind_prefix, self.kind)
    self.name = name
    self.filename = f"{name}.txt"
    self.cc = cc
    self.local = local

  def get_ds_client(self):
    if not self.ds_client:
      self.ds_client = datastore.Client(credentials=service_account.Credentials.from_service_account_file('env_config/client-secret.json'))
    return self.ds_client

  def get_storage_client(self):
    if not self.storage_client:
      self.storage_client = storage.Client(credentials=service_account.Credentials.from_service_account_file('env_config/client-secret.json'))
    return self.storage_client

  def download_file(self, name, fname):
    client = self.get_storage_client()
    bucket = client.get_bucket(GOOGLE_CLOUD_BUCKET)
    blob = bucket.blob(name)
    blob.download_to_file(open(fname, 'wb'))

  def ds_save(self):
    data = {'cloud_config': self.cc}
    m = datastore.Entity(key=self.get_ds_client().key(self.kind, self.name))
    for key, value in data.items():
      if isinstance(value, dict):
        m[key] = 'JSON:' + dump_json(value)
      else:
        m[key] = value
    logger.debug(f"store: {self.kind} - {self.name}")
    self.get_ds_client().put(m)

  def ds_load(self):
    """ Retrieves a cloud config object from datastore """
    result = self.get_ds_client().get(self.get_ds_client().key(self.kind, self.name))
    logger.debug(f"get: {self.kind} - {self.name}")
    try:
      result_out = {'_exists': True}
      for k, v in result.items():
        if isinstance(v, str) and v.startswith("JSON:"):
          result_out[k] = json.loads(v[5:])
        elif v:
          result_out[k] = v
      self.cc = result_out.get('cloud_config')
    except AttributeError:
      return None

  def file_load(self):
    """ Retrieves a cloud config object from a local file """
    if path.exists(self.filename):
      with open(self.filename) as json_file:
        data = json.load(json_file)
        cc = data.get('cloud_config') if data else None
        self.cc = cc

  def file_save(self):
    """ Saves a cloud config object to a local file """
    with open(self.filename, 'w') as outfile:
      data = {'cloud_config': self.cc}
      json.dump(data, outfile)
  
  def save(self):
    if self.local:
      self.file_save()
    else:
      self.ds_save()

  def load(self):
    if self.local:
      self.file_load()
    else:
      self.ds_load()

  def remove_release(self, dataset):
    ''' Removes a data release from the cloud config object '''
    releases = self.cc['releases']
    for i, r in enumerate(releases):
      if r['dataset'] == dataset:
        del releases[i]

    self.cc['releases'] = releases
    self.save()

  def remove_release_files(self, dataset):
    ''' Removes files linked to a data release from the GAE server '''
    report_path = f"base/static/reports/{dataset}"
    if os.path.exists(report_path):
      shutil.rmtree(report_path)

  def remove_release_db(self, dataset, wormbase):
    ''' Removes sqlite db linked to a data release from the GAE server '''
    db_path = f"base/cendr.{dataset}.{wormbase}.db"
    os.remove(db_path)

  def add_release(self, dataset, wormbase, version):
    ''' Adds a data release to the cloud config object '''
    releases = self.cc['releases']
    # remove dataset if there is an existing one in the config
    for i, r in enumerate(releases):
      if r['dataset'] == dataset:
        del releases[i]

    releases = [{'dataset': dataset, 'wormbase': wormbase, 'version': version}] + releases
    self.cc['releases'] = releases
    self.save()

  def get_release_files(self, dataset, files, refresh=False):
    ''' Downloads files linked to a data release from the cloud bucket to the GAE server'''
    local_path = 'base/static/reports/{}'.format(dataset)
    if os.path.exists(local_path):
      if refresh == True:
        shutil.rmtree(local_path)
      else:
        return

    os.makedirs(local_path)
    name_str = 'data_reports/{}/{}'
    fname_str = '{}/{}'
    
    try:
      for n in files:
        name = f"data_reports/{dataset}/{n}"
        fname = f"{local_path}/{n}"
        self.download_file(name=name, fname=fname)
    except:
      return None
    return files

  def get_release_db(self, dataset, wormbase, refresh=False):
    db_name = f"db/cendr.{dataset}.{wormbase}.db"
    db_fname = f"base/cendr.{dataset}.{wormbase}.db"
    if os.path.exists(db_fname):
      if refresh == True:
        os.remove(db_fname)
      else:
        return

    self.download_file(name=db_name, fname=db_fname)
    return True

  def create_backup(self):
    name = self.name
    self.name = '{}_{}'.format(name, unique_id())
    self.save()
    self.name = name

  def get_properties(self):
    ''' Converts the cloud_config object into a format that matches the regular config object '''
    releases = self.cc['releases']
    RELEASES = []
    for r in releases:
      RELEASES.append((r['dataset'], r['wormbase']))
    RELEASES.sort(reverse=True)

    # Set the most recent release
    DATASET_RELEASE, WORMBASE_VERSION = RELEASES[0]

    return {'DATASET_RELEASE': DATASET_RELEASE,
            'WORMBASE_VERSION': WORMBASE_VERSION,
            'RELEASES': RELEASES}
            
  def get_external_content(self):
    releases = self.cc['releases']
    current_release = releases[0]

    # get data reports
    for r in releases:
      files = []
      if r['version'] == 'v1':
        files = REPORT_V1_FILE_LIST
      elif r['version'] == 'v2':
        files = REPORT_V2_FILE_LIST
      self.get_release_files(r['dataset'], files, refresh=False)
    
    # get sqlite db
    self.get_release_db(current_release['dataset'], current_release['wormbase'], refresh=False)

