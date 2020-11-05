# Application Configuration
import os
import yaml
from base.utils.data_utils import json_encoder

# CeNDR Version
APP_CONFIG, CENDR_VERSION = os.environ['GAE_VERSION'].split("-", 1)
if APP_CONFIG not in ['development', 'master']:
    APP_CONFIG = 'development'
CENDR_VERSION = CENDR_VERSION.replace("-", '.')

# BUILDS AND RELEASES
# The first release is the current release
# (RELEASE, ANNOTATION_GENOME)
RELEASES = [("20201015", "WS276"),
            ("20200815", "WS276"),
            ("20180527", "WS263"),
            ("20170531", "WS258"),
            ("20160408", "WS245")]

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
    # Add configuration variables
    # Remove base prefix for SQLAlchemy as it is loaded
    # from application folder
    config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{SQLITE_PATH}".replace("base/", "")
    config['json_encoder'] = json_encoder
    config.update({"CENDR_VERSION": CENDR_VERSION,
                   "APP_CONFIG": APP_CONFIG,
                   "DATASET_RELEASE": DATASET_RELEASE,
                   "WORMBASE_VERSION": WORMBASE_VERSION,
                   "RELEASES": RELEASES})
    return config


# Generate the configuration
config = get_config(APP_CONFIG)
