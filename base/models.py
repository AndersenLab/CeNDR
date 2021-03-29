import os
import re
import arrow
import json
import pandas as pd
import numpy as np
import datetime
import requests
from io import StringIO
from flask import Markup, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func
from werkzeug.security import safe_str_cmp

from base.constants import GOOGLE_CLOUD_BUCKET, STRAIN_PHOTO_PATH
from base.extensions import sqlalchemy
from base.utils.gcloud import get_item, store_item, query_item, get_cendr_bucket, check_blob
from base.utils.aws import get_aws_client
from base.utils.data_utils import hash_password, unique_id
from gcloud.datastore.entity import Entity
from collections import defaultdict
from botocore.exceptions import ClientError

db = SQLAlchemy()

class datastore_model(object):
    """
        Base datastore model

        Google datastore is used to store dynamic information
        such as users and reports.

        Note that the 'kind' must be defined within sub
    """

    def __init__(self, name_or_obj=None):
        """
            Args:
                name_or_obj - A name for a new datastore item
                              or an existing one to initialize
                              using the datastore_model class.
        """
        self.exclude_from_indexes = None
        self._exists = False
        if type(name_or_obj) == Entity:
            # Parse JSON fields when instantiating without
            # loading from gcloud.
            result_out = {}
            for k, v in name_or_obj.items():
                if isinstance(v, str) and v.startswith("JSON:"):
                    result_out[k] = json.loads(v[5:])
                elif v:
                    result_out[k] = v
            self.__dict__.update(result_out)
            self.kind = name_or_obj.key.kind
            self.name = name_or_obj.key.name
        elif name_or_obj:
            self.name = name_or_obj
            item = get_item(self.kind, name_or_obj)
            if item:
                self._exists = True
                self.__dict__.update(item)

    def save(self):
        self._exists = True
        item_data = {k: v for k, v in self.__dict__.items() if k not in ['kind', 'name'] and not k.startswith("_")}
        store_item(self.kind, self.name, **item_data)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def __repr__(self):
        if hasattr(self, 'name'):
            return f"<{self.kind}:{self.name}>"
        else:
            return f"<{self.kind}:no-name>"


class trait_ds(datastore_model):
    """
        Trait class corresponds to a trait analysis within a report.
        This class contains methods for submitting jobs and fetching results
        for an analysis.

        If a task is re-run the report will only display the latest version.
    """
    kind = 'trait'

    def __init__(self, *args, **kwargs):
        """
            The trait_ds object adopts the task
            ID assigned by AWS Fargate.
        """
        self._ecs = get_aws_client('ecs')
        # Get task status
        self._logs = get_aws_client('logs')
        super(trait_ds, self).__init__(*args, **kwargs)
        self.exclude_from_indexes = ['trait_data', 'error_traceback', 'CEGWAS_VERSION', 'task_info']
        # Read trait data in upon initialization.
        if hasattr(self, 'trait_data'):
            self._trait_df = pd.read_csv(StringIO(self.trait_data), sep='\t')

    def version_link(self):
        """
            Returns the data version link.
        """
        release_link = url_for('data.data', selected_release=self.DATASET_RELEASE)
        return Markup(f"<a href='{release_link}'>{self.DATASET_RELEASE}</a>")

    def run_task(self):
        """
            Runs the task
        """
        # Fargate credentials
        task_fargate = self._ecs.run_task(
            taskDefinition=f"cendr-map-{DATASET_RELEASE}",
            overrides={
                'containerOverrides': [
                    {
                        'name': 'cegwas',
                        'command': [
                            'python3',
                            'run.py'
                        ],
                        'environment': [
                            {
                                'name': 'GOOGLE_APPLICATION_CREDENTIALS',
                                'value': 'gcloud_fargate.json'
                            },
                            {
                                'name': 'REPORT_NAME',
                                'value': self.report_name
                            },
                            {
                                'name': 'TRAIT_NAME',
                                'value': self.trait_name
                            },
                            {
                                'name': 'DATASET_RELEASE',
                                'value': DATASET_RELEASE
                            }
                        ],
                    }
                ],
            },
            count=1,
            launchType='FARGATE',
            networkConfiguration={
                'awsvpcConfiguration': {
                    'subnets': [
                        'subnet-77581612',
                    ],
                    'securityGroups': [
                        'sg-75e7860a'
                    ],
                    'assignPublicIp': 'ENABLED'
                }
            })
        task_fargate = task_fargate['tasks'][0]

        # Generate trait_ds model
        self.report_trait = "{}:{}".format(self.report_name, self.trait_name)
        self.name = task_fargate['taskArn'].split("/")[1]
        self.task_info = task_fargate
        self.created_on = arrow.utcnow().datetime

        self.save()
        # Return the task ID
        return self.name

    def container_status(self):
        """
            Fetch the status of the task
        """
        if self.status == 'complete':
            return 'complete'
        try:
            task_status = self._ecs.describe_tasks(tasks=[self.name])['tasks'][0]['lastStatus']
            return task_status
        except (IndexError, ClientError):
            return 'STOPPED'

    @property
    def is_complete(self):
        return self.status == "complete"

    @property
    def cegwas_version_formatted(self):
        try:
            git_hash = self.CEGWAS_VERSION[3].replace("(Andersenlab/cegwas@", "").replace(")", "")
            return f"v{self.CEGWAS_VERSION[0]} @{git_hash} [{self.CEGWAS_VERSION[1]}]"
        except:
            return ""

    @property
    def docker_image_version(self):
        try:
            return json.loads(self.task_info[5:])['containers'][0]['containerArn'].split("/")[1]
        except:
            return ""

    def get_formatted_task_log(self):
        """
            Returns formatted task log
        """
        try:
            log = requests.get(self.gs_base_url + "/out.log").content
        except:
            return [f"####-##-## ##:##:## Task ID: {self.name}\n"]
        return (f"####-##-## ##:##:## Task ID: {self.name}\n" + log.decode('utf-8')).splitlines()

    def duration(self):
        """
            Calculate how long the run took
        """
        if hasattr(self, 'completed_on') and hasattr(self, 'started_on'):
            diff = (self.completed_on - self.started_on)
            minutes, seconds = divmod(diff.seconds, 60)
            return "{:0>2d}m {:0>2d}s".format(minutes, seconds)
        else:
            return None

    @property
    def gs_path(self):
        if self.REPORT_VERSION == 'v2':
            return f"{self.REPORT_VERSION}/{self.name}"
        elif self.REPORT_VERSION == 'v1':
            return f"{self.REPORT_VERSION}/{self.report_slug}/{self.trait_name}"

    @property
    def gs_base_url(self):
        """
            Returns the google storage base URL

            The URL schema changed from REPORT_VERSION v1 to v2.
        """
        if self.REPORT_VERSION == 'v2':
            return f"https://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/reports/{self.gs_path}"
        elif self.REPORT_VERSION == 'v1':
            return f"https://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/reports/{self.gs_path}"

    def get_gs_as_dataset(self, fname):
        """
            Downloads a dataset stored as a TSV
            from the folder associated with the trait
            on google storage and return it as a
            pandas dataframe.
        """
        return pd.read_csv(f"{self.gs_base_url}/{fname}", sep="\t")

    def get_gs_as_json(self, fname):
        """
            Downloads a google-storage file as json
        """
        return requests.get(f"{self.gs_base_url}/{fname}").json()

    def list_report_files(self):
        """
            Lists files with a given prefix
            from the current dataset release
        """

        cendr_bucket = get_cendr_bucket()
        items = cendr_bucket.list_blobs(prefix=f"reports/{self.gs_path}")
        return {os.path.basename(x.name): f"https://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/{x.name}" for x in items}

    def file_url(self, fname):
        """
            Return the figure URL. May change with updates
            to report versions.
        """
        gs_url = f"{self.gs_base_url}/{fname}"
        return f"{gs_url}"


class mapping_ds(datastore_model):
    """
        The mapping/peak interval model
    """
    kind = 'mapping'
    
    def __init__(self, *args, **kwargs):
        super(mapping_ds, self).__init__(*args, **kwargs)


class user_ds(datastore_model):
    """
        The User model - for creating and retrieving
        information on users.
    """
    kind = 'user'
    
    def __init__(self, *args, **kwargs):
        super(user_ds, self).__init__(*args, **kwargs)


    def set_properties(self, **kwargs):
        if 'username' in kwargs:
            self.username = kwargs.get('username')
        if 'full_name' in kwargs:
            self.full_name = kwargs.get('full_name')
        if 'password' in kwargs:
            self.set_password(kwargs.get('password'), kwargs.get('salt'))
        if 'email' in kwargs:
            self.set_email(kwargs.get('email'))
        if 'roles' in kwargs:
            self.roles = kwargs.get('roles')

    def save(self, *args, **kwargs):
        now = arrow.utcnow().datetime
        if not self._exists:
            self.created_on = now
        self.modified_on = now
        super(user_ds, self).save(*args, **kwargs)

    def reports(self):
        filters = [('user_id', '=', self.name)]
        # Note this requires a composite index defined very precisely.
        results = query_item('trait', filters=filters, order=['user_id', '-created_on'])
        results = sorted(results, key=lambda x: x['created_on'], reverse=True)
        results_out = defaultdict(list)
        for row in results:
            results_out[row['report_slug']].append(row)
        # Generate report objects
        return results_out

    def get_all(keys_only=False):
        results = query_item('user', keys_only=keys_only)
        return results

    def set_password(self, password, salt):
        # calling set_password with self.password 
        if hasattr(self, 'password'):
            if (len(password) > 0) and (password != self.password):
                self.password = hash_password(password + salt)
        else:
            self.password = hash_password(password + salt)

    def set_email(self, email):
        if hasattr(self, 'email'):
            if not safe_str_cmp(email, self.email):
                self.email = email
                self.email_confirmation_code = unique_id()
                self.verified_email = False
        else:
            self.email = email
            self.email_confirmation_code = unique_id()
            self.verified_email = False

    def check_password(self, password, salt):
        return safe_str_cmp(self.password, hash_password(password + salt))
    

class markdown_ds(datastore_model):
    """
        The Markdown model - for creating and retrieving
        documents uploaded to the site
    """
    kind = 'markdown'
    
    def __init__(self, *args, **kwargs):
      super(markdown_ds, self).__init__(*args, **kwargs)

    def get_all(keys_only=False):
      results = query_item('markdown', keys_only=keys_only)
      return results

    def query_by_type(type, keys_only=False):
      filters = [('type', '=', type)]
      results = query_item('markdown', filters=filters, keys_only=keys_only)
      return results

    def save(self, *args, **kwargs):
      now = arrow.utcnow().datetime
      self.modified_on = now
      if not self._exists:
        self.created_on = now
      super(markdown_ds, self).save(*args, **kwargs)


class data_report_ds(datastore_model):
  """
      The Data Report model - for creating and retrieving
      releases of genomic data
  """
  kind = 'data-report'

  def init(self):
    self.dataset = ''
    self.wormbase = ''
    self.version = ''
    self.initialized = False
    self.published_on = ''
    self.publish = False
    self.created_on = arrow.utcnow().datetime
    self.report_synced_on = ''
    self.db_synced_on = ''

  def __init__(self, *args, **kwargs):
    super(data_report_ds, self).__init__(*args, **kwargs)

  def get_all(keys_only=False):
    results = query_item('data-report', keys_only=keys_only)
    return results

  def list_bucket_dirs():
    """
        Lists 'directories' in GCP Bucket 'data_reports' (unique blob prefixes matching date format)
    """
    cendr_bucket = get_cendr_bucket()
    items = cendr_bucket.list_blobs(prefix=f"data_reports/")
    dirs = []
    pattern = r"^(data_reports\/)([0-9]{8})/"
    for i in items:
      match = re.search(pattern, i.name)
      if match:
        dir = match.group(2)
        if not dir in dirs:
          dirs.append(dir)
      
    return dirs

  def save(self, *args, **kwargs):
    now = arrow.utcnow().datetime
    self.modified_on = now
    super(data_report_ds, self).save(*args, **kwargs)


class config_ds(datastore_model):
  """
      The Data Config model - Config stored in the cloud
      for the site's data sources
  """
  kind = 'config'

  def __init__(self, *args, **kwargs):
    super(config_ds, self).__init__(*args, **kwargs)

  def save(self, *args, **kwargs):
    now = arrow.utcnow().datetime
    self.modified_on = now
    if not self._exists:
      self.created_on = now
    super(config_ds, self).save(*args, **kwargs)

class DictSerializable(object):
  def _asdict(self):
    result = {}
    for key in self.__mapper__.c.keys():
      result[key] = getattr(self, key)
    return result

# --------- Break datastore here ---------#

class Metadata(DictSerializable, db.Model):
    """
        Table for storing information about other tables
    """
    __tablename__ = "metadata"
    key = db.Column(db.String(50), index=True, primary_key=True)
    value = db.Column(db.String)																								


class Strain(DictSerializable, db.Model):
    __tablename__ = "strain"
    species_id_method = db.Column(db.String(50), nullable=True)
    species = db.Column(db.String(50), index=True)
    isotype_ref_strain = db.Column(db.Boolean(), index=True)
    strain = db.Column(db.String(25), primary_key=True)
    isotype = db.Column(db.String(25), index=True, nullable=True)
    previous_names = db.Column(db.String(100), nullable=True)
    sequenced = db.Column(db.Boolean(), index=True, nullable=True)  # Is whole genome sequenced [WGS_seq]
    
    release = db.Column(db.Integer(), nullable=False, index=True)
    source_lab = db.Column(db.String(), nullable=True)
    
    latitude = db.Column(db.Float(), nullable=True)
    longitude = db.Column(db.Float(), nullable=True)
    landscape = db.Column(db.String(), nullable=True)
    locality_description = db.Column(db.String(), nullable=True)

    substrate = db.Column(db.String(), nullable=True)
    substrate_comments = db.Column(db.String(), nullable=True)
    substrate_temp = db.Column(db.Float())
    ambient_temp = db.Column(db.Float())
    ambient_humidity = db.Column(db.Float())
    
    associated_organism = db.Column(db.String(), nullable=True)
    inbreeding_status = db.Column(db.String(), nullable=True)
        
    sampled_by = db.Column(db.String(), nullable=True)
    isolated_by = db.Column(db.String(), nullable=True)
    sampling_date = db.Column(db.Date(), nullable=True)
    sampling_date_comment = db.Column(db.String(), nullable=True)
    notes = db.Column(db.String(), nullable=True)
    strain_set = db.Column(db.String(), nullable=True)
    issues = db.Column(db.Boolean(), nullable=True)
    issue_notes = db.Column(db.String(), nullable=True)

    # Elevation is added in and computed separately
    elevation = db.Column(db.Float(), nullable=True)

    def __repr__(self):
        return self.strain

    def to_json(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def strain_photo_url(self):
        # Checks if photo exists and returns URL if it does
        try:
            return check_blob(f"{STRAIN_PHOTO_PATH}{self.strain}.jpg").public_url
        except AttributeError:
            return None

    def strain_thumbnail_url(self):
        # Checks if thumbnail exists and returns URL if it does
        try:
            return check_blob(f"{STRAIN_PHOTO_PATH}{self.strain}.thumb.jpg").public_url
        except AttributeError:
            return None

    def strain_bam_url(self):
        """
            Return bam / bam_index url set
        """
        bam_file=self.strain + '.bam'
        bai_file=self.strain + '.bam.bai'
        bam_download_link = url_for('data.download_bam_url', blob_name=bam_file)
        bai_download_link = url_for('data.download_bam_url', blob_name=bai_file)
        url_set = Markup(f"""
                        <a href="{ bam_download_link }" target="_blank">
                            BAM
                        </a>
                        /
                        <a href="{ bai_download_link }" target="_blank">
                            bai
                        </a>
                   """.strip())
        return url_set

    @classmethod
    def strain_sets(cls):
        df = pd.read_sql_table(cls.__tablename__, db.engine)
        result = df[['strain', 'isotype', 'strain_set']].dropna(how='any') \
                                             .groupby('strain_set') \
                                             .agg(list) \
                                             .to_dict()
        return result['strain']


    def isotype_bam_url(self):
        """
            Return bam / bam_index url set
        """
        bam_file=self.isotype + '.bam'
        bai_file=self.isotype + '.bam.bai'
        bam_download_link = url_for('data.download_bam_url', blob_name=bam_file)
        bai_download_link = url_for('data.download_bam_url', blob_name=bai_file)
        url_set = Markup(f"""
                        <a href="{ bam_download_link }" target="_blank">
                            BAM
                        </a>
                        /
                        <a href="{ bai_download_link }" target="_blank">
                            bai
                        </a>
                   """.strip())
        return url_set

    @classmethod
    def cum_sum_strain_isotype(cls):
        """
            Create a time-series plot of strains and isotypes collected over time

            Args:
                df - the strain dataset
        """
        df = pd.read_sql_table(cls.__tablename__, db.engine)
        # Remove strains with issues
        df = df[df["issues"] == False]
        cumulative_isotype = df[['isotype', 'sampling_date']].sort_values(['sampling_date'], axis=0) \
                                                             .drop_duplicates(['isotype']) \
                                                             .groupby(['sampling_date'], as_index=True) \
                                                             .count() \
                                                             .cumsum() \
                                                             .reset_index()
        cumulative_isotype = cumulative_isotype.append({'sampling_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                        'isotype': len(df['isotype'].unique())}, ignore_index=True)
        cumulative_strain = df[['strain', 'sampling_date']].sort_values(['sampling_date'], axis=0) \
                                                           .drop_duplicates(['strain']) \
                                                           .dropna(how='any') \
                                                           .groupby(['sampling_date']) \
                                                           .count() \
                                                           .cumsum() \
                                                           .reset_index()
        cumulative_strain = cumulative_strain.append({'sampling_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                      'strain': len(df['strain'].unique())}, ignore_index=True)
        df = cumulative_isotype.set_index('sampling_date') \
                               .join(cumulative_strain.set_index('sampling_date')) \
                               .reset_index()
        return df
        

    @classmethod
    def release_summary(cls, release):
        """
            Returns isotype and strain count for a data release.

            Args:
                release - the data release
        """
        counts = {'strain_count': cls.query.filter((cls.release <= release) & (cls.issues == False)).count(),
                  'strain_count_sequenced': cls.query.filter((cls.release <= release) & (cls.issues == False) & (cls.sequenced == True)).count(),
                  'isotype_count': cls.query.filter((cls.release <= release) & (cls.issues == False) & (cls.isotype != None)).group_by(cls.isotype).count()}
        return counts

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class WormbaseGene(DictSerializable, db.Model):
    __tablename__ = 'wormbase_gene'
    id = db.Column(db.Integer, primary_key=True)
    chrom = db.Column(db.String(20), index=True)
    chrom_num = db.Column(db.Integer(), index=True)  # For sorting purposes
    start = db.Column(db.Integer(), index=True)
    end = db.Column(db.Integer(), index=True)
    feature = db.Column(db.String(30), index=True)
    strand = db.Column(db.String(1))
    frame = db.Column(db.Integer(), nullable=True)
    gene_id = db.Column(db.ForeignKey('wormbase_gene_summary.gene_id'), nullable=False)
    gene_biotype = db.Column(db.String(30), nullable=True)
    locus = db.Column(db.String(30), index=True)
    transcript_id = db.Column(db.String(30), nullable=True, index=True)
    transcript_biotype = db.Column(db.String(), index=True)
    exon_id = db.Column(db.String(30), nullable=True, index=True)
    exon_number = db.Column(db.Integer(), nullable=True)
    protein_id = db.Column(db.String(30), nullable=True, index=True)
    arm_or_center = db.Column(db.String(12), index=True)

    gene_summary = db.relationship("WormbaseGeneSummary", backref='gene_components')

    def __repr__(self):
        return f"{self.gene_id}:{self.feature} [{self.seqname}:{self.start}-{self.end}]"


class WormbaseGeneSummary(DictSerializable, db.Model):
    """
        This is a condensed version of the WormbaseGene model;
        It is constructed out of convenience and only defines the genes
        (not exons/introns/etc.)
    """
    __tablename__ = "wormbase_gene_summary"
    id = db.Column(db.Integer, primary_key=True)
    chrom = db.Column(db.String(7), index=True)
    chrom_num = db.Column(db.Integer(), index=True)
    start = db.Column(db.Integer(), index=True)
    end = db.Column(db.Integer(), index=True)
    locus = db.Column(db.String(30), index=True)
    gene_id = db.Column(db.String(25), index=True)
    gene_id_type = db.Column(db.String(15), index=False)
    sequence_name = db.Column(db.String(30), index=True)
    biotype = db.Column(db.String(30), nullable=True)
    gene_symbol = db.column_property(func.coalesce(locus, sequence_name, gene_id))
    interval = db.column_property(func.printf("%s:%s-%s", chrom, start, end))
    arm_or_center = db.Column(db.String(12), index=True)

    @classmethod
    def resolve_gene_id(cls, query):
        """
            query - a locus name or transcript ID
            output - a wormbase gene ID

            Example:
            WormbaseGene.resolve_gene_id('pot-2') --> WBGene00010195
        """
        result = cls.query.filter(or_(cls.locus == query, cls.sequence_name == query)).first()
        if result:
            return result.gene_id


class Homologs(DictSerializable, db.Model):
    """
        The homologs database combines
    """
    __tablename__ = "homologs"
    id = db.Column(db.Integer, primary_key=True)
    gene_id = db.Column(db.ForeignKey('wormbase_gene_summary.gene_id'), nullable=False, index=True)
    gene_name = db.Column(db.String(40), index=True)
    homolog_species = db.Column(db.String(50), index=True)
    homolog_taxon_id = db.Column(db.Integer, index=True, nullable=True)  # If available
    homolog_gene = db.Column(db.String(50), index=True)
    homolog_source = db.Column(db.String(40))

    gene_summary = db.relationship("WormbaseGeneSummary", backref='homologs', lazy='joined')

    def unnest(self):
        """
            Used with the gene API - returns
            an unnested homolog datastructure combined with the wormbase gene summary model.
        """
        self.__dict__.update(self.gene_summary.__dict__)
        self.__dict__['gene_summary'] = None
        return self

    def __repr__(self):
        return f"homolog: {self.gene_name} -- {self.homolog_gene}"
