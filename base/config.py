# Application Configuration
import os
import yaml
from base.utils.data_utils import json_encoder
from base.constants import DEFAULT_CLOUD_CONFIG
from base.cloud_config import CloudConfig

# Whether or not to load config properties from cloud datastore
try:
  CLOUD_CONFIG = os.environ['CLOUD_CONFIG']
except:
  CLOUD_CONFIG = 0

# CeNDR Version
APP_CONFIG, CENDR_VERSION = os.environ['GAE_VERSION'].split("-", 1)
if APP_CONFIG not in ['development', 'master']:
  APP_CONFIG = 'development'
CENDR_VERSION = CENDR_VERSION.replace("-", '.')

# BUILDS AND RELEASES
# The first release is the current release
# (RELEASE, ANNOTATION_GENOME)
RELEASES = [("20210121", "WS276"), ("20200815", "WS276"), ("20180527", "WS263"), ("20170531", "WS258"), ("20160408", "WS245")]

# The most recent release
DATASET_RELEASE, WORMBASE_VERSION = RELEASES[0]

# SQLITE DATABASE
SQLITE_PATH = f"base/cendr.{DATASET_RELEASE}.{WORMBASE_VERSION}.db"

def load_yaml(path):
  return yaml.load(open(path), Loader=yaml.SafeLoader)

# CONFIG
def get_config(APP_CONFIG):
  """Load all configuration information including
  constants defined above.

  (BASE_VARS are the same regardless of whether we are debugging or in production)
  """
  config = dict()
  BASE_VARS = load_yaml("env_config/base.yaml")
  APP_CONFIG_VARS = load_yaml(f"env_config/{APP_CONFIG}.yaml")
  config.update(BASE_VARS)
  config.update(APP_CONFIG_VARS)

  config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{SQLITE_PATH}".replace("base/", "")
  config['json_encoder'] = json_encoder
  config.update({"CENDR_VERSION": CENDR_VERSION,
                  "APP_CONFIG": APP_CONFIG,
                  "DATASET_RELEASE": DATASET_RELEASE,
                  "WORMBASE_VERSION": WORMBASE_VERSION,
                  "RELEASES": RELEASES})

  config['DS_PREFIX'] = ''
  if APP_CONFIG == 'development':
    config['DS_PREFIX'] = 'DEV_'
  cc = None
  local = True if CLOUD_CONFIG == 1 else False
  # Add configuration variables from cloud
  cc = CloudConfig(DEFAULT_CLOUD_CONFIG, kind_prefix=config['DS_PREFIX'], local=local)
  cc.load()
  cc.get_external_content()
  props = cc.get_properties()
  config.update(props)
  config['cloud_config'] = cc
    
  return config


config = get_config(APP_CONFIG)
