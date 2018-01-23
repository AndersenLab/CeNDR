import arrow
import pandas as pd
import numpy as np
import datetime
from io import StringIO
from flask import Markup, url_for
from sqlalchemy import or_, func

from base.application import db_2
from base.constants import URLS
from base.utils.gcloud import get_item, store_item, query_item
from base.utils.aws import get_aws_client
from gcloud.datastore.entity import Entity

from logzero import logger

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
            self.__dict__.update(name_or_obj)
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

    def __repr__(self):
        return f"<{self.kind}:{self.name}>"


class report_m(datastore_model):
    """
        The report model - for creating and retreiving
        information on reports
    """
    kind = 'report'
    def __init__(self, *args, **kwargs):
        super(report_m, self).__init__(*args, **kwargs)
        self.exclude_from_indexes = ('trait_data', 'strain_list')
        # Read trait data in upon initialization.
        if hasattr(self, 'trait_data'):
            self._trait_df = pd.read_csv(StringIO(self.trait_data), sep='\t')

    def trait_strain_count(self, trait_slug):
        """
            Return number of strains submitted for a trait.
        """
        return self._trait_df[trait_slug].count()

    def humanize(self):
        return arrow.get(self.created_on).humanize()


    def fetch_traits(self, trait_name=None, latest=True):
        """
            Fetches trait/task records associated with a report.

            Args:
                trait_name - Fetches a specific trait
                latest - Returns only the first record of each trait.

            Returns
                If a trait name is given, and latest - ONE result
                If latest - one result for each trait
                if neight - all tasks associated with a report.
        """
        report_filter = [('report_slug', '=', self.name)]
        if trait_name:
            trait_list = [trait_name]
        else:
            trait_list = self.trait_list
        result_out = []
        for trait in trait_list:
            trait_filters = report_filter + [('trait_name', '=', trait)]
            results = list(query_item('trait',
                                      filters=trait_filters,
                                      order=['report_slug', 'trait_name', '-created_on']))
            if results:
                if trait_name and latest:
                    result_out = trait_m(results[0].key.name)
                elif latest:
                    result_out.append(trait_m(results[0].key.name))
                else:
                    for result in results:
                        result_out.append(result)
        return result_out


    def fetch_trait_status(self):
        """
            If traits-tasks are still being run
            this function will fetch and update their status.

            Once they have completed it will cache the result    
        """
        traits = self.fetch_traits(latest=True)
        self.trait_run_status = {x.trait_name: x.run_status for x in traits}
        self.save()
        return self.trait_run_status


class trait_m(datastore_model):
    """
        Trait class corresponds to a trait analysis within a report.
        This class contains methods for submitting jobs and fetching results
        for an analysis.

        If a task is re-run the report will only display the latest version.
    """
    kind = 'trait'
    def __init__(self, *args, **kwargs):
        """
            The trait_m object adopts the task
            ID assigned by AWS Fargate.
        """
        self._ecs = get_aws_client('ecs')
        self._logs = get_aws_client('logs')
        super(trait_m, self).__init__(*args, **kwargs)

    def version_link(self):
        release_link = url_for('data.data', selected_release= self.data_release)
        return Markup(f"<a href='{release_link}'>{self.data_release}</a>")


    def run_task(self):
        """
            Runs the task
        """
        task_fargate = self._ecs.run_task(
        taskDefinition='cendr-map',
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
        }
        )
        try:
            task_fargate = task_fargate['tasks'][0]
        except KeyError:
            # Something went wrong.
            return None

        # Generate trait_m model
        self.report_trait = "{}:{}".format(self.report_name, self.trait_name)
        self.name = task_fargate['taskArn'].split("/")[1]
        self.task_info = task_fargate
        self.created_on = arrow.utcnow().datetime

        self.save()
        # Return the task ID
        return self.name

    def status(self):
        """
            Fetch the status of the task
        """
        task_status = self._ecs.describe_tasks(tasks=[self.name])['tasks'][0]
        return task_status


    def get_task_log(self):
        """
            Returns the task log associated with
            the task.
        """
        try:
            print(f"ecs/cegwas/{self.name}")
            print('/ecs/cendr-map')
            log = self._logs.get_log_events(logGroupName='/ecs/cendr-map',
                                            logStreamName=f"ecs/cegwas/{self.name}",
                                            limit=10000)
            return log.get('events')
        except self._logs.exceptions.ResourceNotFoundException:
            return None


    def get_formatted_task_log(self):
        """
            Returns formatted task log
        """
        logs = self.get_task_log()
        yield f"####-##-## ##:##:## Task ID: {self.name}"
        if logs:
            for log in logs:
                timestamp = int(str(log['timestamp'])[:-3])
                event_time = arrow.Arrow.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%m:%S")
                yield f"{event_time} {log['message']}"
        else:
            return []

    def duration(self):
        """
            Calculate how long the run took
        """
        if hasattr(self, 'completed_on') and hasattr(self, 'started_on'):
            diff = (self.completed_on - self.started_on)
            minutes, seconds = divmod(diff.seconds, 60*60*24)
            return "{:0>2d}m {:0>2d}s".format(minutes, seconds)
        else:
            return None


"""

from base.models2 import trait_m

t = trait_m()
t.report_name = 'test-report'
t.trait_name = 'yeah1'
t.run_task()

"""
class user_m(datastore_model):
    """
        The User model - for creating and retrieving
        information on users.
    """
    kind = 'user'
    def __init__(self, *args, **kwargs):
        super(user_m, self).__init__(*args, **kwargs)

    def reports(self):
        filters = [('user_id', '=', self.user_id)]
        # Note this requires a composite index defined very precisely.
        results = query_item('report', filters=filters, order=['user_id', '-created_on'])

        # Generate report objects
        return [report_m(x) for x in results]



class metadata_m(db_2.Model):
    """
        Table for storing information about other tables
    """
    __tablename__ = "metadata"
    key = db_2.Column(db_2.String(50), index=True, primary_key=True)
    value = db_2.Column(db_2.String)



class strain_m(db_2.Model):
    __tablename__ = "strain"
    strain = db_2.Column(db_2.String(25), primary_key=True)
    reference_strain = db_2.Column(db_2.Boolean(), index=True)
    isotype = db_2.Column(db_2.String(25), index=True, nullable=True)
    previous_names = db_2.Column(db_2.String(100), nullable=True)
    source_lab = db_2.Column(db_2.String(), nullable=True)
    release = db_2.Column(db_2.Integer(), nullable=False, index=True)
    latitude = db_2.Column(db_2.Float(), nullable=True)
    longitude = db_2.Column(db_2.Float(), nullable=True)
    elevation = db_2.Column(db_2.Float(), nullable=True)
    landscape = db_2.Column(db_2.String(), nullable=True)
    substrate = db_2.Column(db_2.String(), nullable=True)
    photo = db_2.Column(db_2.String(), nullable=True)
    isolated_by = db_2.Column(db_2.String(), nullable=True)
    sampled_by = db_2.Column(db_2.String(), nullable=True)
    isolation_date = db_2.Column(db_2.Date(), nullable=True)
    isolation_date_comment = db_2.Column(db_2.String(), nullable=True)
    notes = db_2.Column(db_2.String(), nullable=True)
    sets = db_2.Column(db_2.String(), nullable=True)

    def __repr__(self):
        return self.strain

    def list_sets(self):
        if self.sets:
            return self.sets.split(",")
        else:
            return []

    def bam_url(self):
        """
            Return bam / bam_index url set
        """

        url_set = Markup(f"""
                        <a href="{URLS.BAM_URL_PREFIX}/{self.isotype}.bam">
                            BAM
                        </a>
                        /
                        <a href="{URLS.BAM_URL_PREFIX}/{self.isotype}.bam.bai">
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
        df = pd.read_sql_table(cls.__tablename__, db_2.engine)
        cumulative_isotype = df[['isotype', 'isolation_date']].sort_values(['isolation_date'], axis=0) \
                                                          .drop_duplicates(['isotype']) \
                                                          .groupby(['isolation_date'], as_index=True) \
                                                          .count() \
                                                          .cumsum() \
                                                          .reset_index()
        cumulative_isotype = cumulative_isotype.append({'isolation_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                        'isotype': len(df['isotype'].unique())}, ignore_index=True)
        cumulative_strain = df[['strain', 'isolation_date']].sort_values(['isolation_date'], axis=0) \
                                                            .drop_duplicates(['strain']) \
                                                            .dropna(how='any') \
                                                            .groupby(['isolation_date']) \
                                                            .count() \
                                                            .cumsum() \
                                                            .reset_index()
        cumulative_strain = cumulative_strain.append({'isolation_date': np.datetime64(datetime.datetime.today().strftime("%Y-%m-%d")),
                                                      'strain': len(df['strain'].unique())}, ignore_index=True)
        df = cumulative_isotype.set_index('isolation_date') \
                               .join(cumulative_strain.set_index('isolation_date')) \
                               .reset_index()
        return df


class wormbase_gene_m(db_2.Model):
    __tablename__ = 'wormbase_gene'
    id = db_2.Column(db_2.Integer, primary_key=True)
    chrom = db_2.Column(db_2.String(20), index=True)
    chrom_num = db_2.Column(db_2.Integer(), index=True)  # For sorting purposes
    start = db_2.Column(db_2.Integer(), index=True)
    end = db_2.Column(db_2.Integer(), index=True)
    feature = db_2.Column(db_2.String(30), index=True)
    strand = db_2.Column(db_2.String(1))
    frame = db_2.Column(db_2.Integer(), nullable=True)
    gene_id = db_2.Column(db_2.ForeignKey('wormbase_gene_summary_m.gene_id'), nullable=False)
    gene_biotype = db_2.Column(db_2.String(30), nullable=True)
    locus = db_2.Column(db_2.String(30), index=True)
    transcript_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    transcript_biotype = db_2.Column(db_2.String(), index=True)
    exon_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    exon_number = db_2.Column(db_2.Integer(), nullable=True)
    protein_id = db_2.Column(db_2.String(30), nullable=True, index=True)
    arm_or_center = db_2.Column(db_2.String(12), index=True)

    gene_summary = db_2.relationship("wormbase_gene_summary_m", backref='gene_components')


    def __repr__(self):
        return f"{self.gene_id}:{self.feature} [{self.seqname}:{self.start}-{self.end}]"


class wormbase_gene_summary_m(db_2.Model):
    """
        This is a condensed version of the wormbase_gene_m model;
        It is constructed out of convenience and only defines the genes
        (not exons/introns/etc.)
    """
    id = db_2.Column(db_2.Integer, primary_key=True)
    chrom = db_2.Column(db_2.String(7), index=True)
    chrom_num = db_2.Column(db_2.Integer(), index=True)
    start = db_2.Column(db_2.Integer(), index=True)
    end = db_2.Column(db_2.Integer(), index=True)
    locus = db_2.Column(db_2.String(30), index=True)
    gene_id = db_2.Column(db_2.String(25), index=True)
    gene_id_type = db_2.Column(db_2.String(15), index=False)
    sequence_name = db_2.Column(db_2.String(30), index=True)
    biotype = db_2.Column(db_2.String(30), nullable=True)
    gene_symbol = db_2.column_property(func.coalesce(locus, sequence_name, gene_id))
    arm_or_center = db_2.Column(db_2.String(12), index=True)

    @classmethod
    def resolve_gene_id(cls, query):
        """
            query - a locus name or transcript ID
            output - a wormbase gene ID

            Example:
            wormbase_gene_m.resolve_gene_id('pot-2') --> WBGene00010195
        """
        result = cls.query.filter(or_(cls.locus == query, cls.sequence_name == query)).first()
        if result:
            return result.gene_id



class homologs_m(db_2.Model):
    """
        The homologs database combines 
    """
    id = db_2.Column(db_2.Integer, primary_key=True)
    gene_id = db_2.Column(db_2.ForeignKey('wormbase_gene_summary_m.gene_id'), nullable=False, index=True)
    gene_name = db_2.Column(db_2.String(40), index=True)
    homolog_species = db_2.Column(db_2.String(50), index=True)
    homolog_taxon_id = db_2.Column(db_2.Integer, index=True, nullable=True) # If available    
    homolog_gene = db_2.Column(db_2.String(50), index=True)
    homolog_source = db_2.Column(db_2.String(40))

    gene_summary = db_2.relationship("wormbase_gene_summary_m", backref='homologs', lazy='joined')

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


