import requests

from datetime import timedelta
from base.utils.jwt import jwt_required
from simplejson.errors import JSONDecodeError
from flask import make_response, render_template, Blueprint

from base.config import config
from base.constants import GOOGLE_CLOUD_BUCKET
from base.views.api.api_strain import get_isotypes, query_strains
from base.models import Strain
from base.utils.gcloud import list_release_files, generate_download_signed_url_v4

data_bp = Blueprint('data',
                    __name__,
                    template_folder='data')

# ============= #
#   Data Page   #
# ============= #

@data_bp.route('/release/latest')
@data_bp.route('/release/<string:selected_release>')
def data(selected_release=None):
    """
        Default data page - lists
        available releases.
    """
    if selected_release is None:
      selected_release = config['DATASET_RELEASE']

    # Pre-2020 releases used BAMs grouped by isotype.
    if int(selected_release) < 20200101:
        return data_v01(selected_release)
    
    # Post-2020 releases keep strain-level bams separate.
    title = "Genomic Data"
    sub_page = selected_release
    strain_listing = query_strains(release=selected_release)
    release_summary = Strain.release_summary(selected_release)
    RELEASES = config["RELEASES"]
    DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == selected_release, RELEASES))[0]
    REPORTS = ["alignment"]
    return render_template('data_v2.html', **locals())


def data_v01(selected_release):
    # Legacy releases (Pre 20200101)
    title = "Genomic Data"
    subtitle = selected_release
    strain_listing = query_strains(release=selected_release)
    # Fetch variant data
    url = f"https://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/releases/{selected_release}/multiqc_bcftools_stats.json"
    try:
        vcf_summary = requests.get(url).json()
    except JSONDecodeError:
        vcf_summary = None
    release_summary = Strain.release_summary(selected_release)
    try:
        phylo_url = list_release_files(f"releases/{config['DATASET_RELEASE']}/popgen/trees/genome.pdf")[0]
    except IndexError:
        phylo_url = None
    RELEASES = config["RELEASES"]
    wormbase_genome_version = dict(config["RELEASES"])[selected_release]
    return render_template('data.html', **locals())

# ======================= #
#   Alignment Data Page   #
# ======================= #
@data_bp.route('/release/latest/alignment')
@data_bp.route('/release/<string:selected_release>/alignment')
def alignment_data(selected_release=None):
    """
        Alignment data page
    """
    if selected_release is None:
      selected_release = config['DATASET_RELEASE']
    # Pre-2020 releases don't have data organized the same way
    if int(selected_release) < 20200101:
        return 
    
    # Post-2020 releases
    title = "Alignment Data"
    strain_listing = query_strains(release=selected_release)
    RELEASES = config["RELEASES"]
    DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == selected_release, RELEASES))[0]
    REPORTS = ["alignment"]
    return render_template('alignment.html', **locals())

# =========================== #
#   Strain Issues Data Page   #
# =========================== #
@data_bp.route('/release/latest/strain_issues')
@data_bp.route('/release/<string:selected_release>/strain_issues')
def strain_issues(selected_release=None):
    """
        Strain Issues page
    """
    if selected_release is None:
      selected_release = config['DATASET_RELEASE']
    # Pre-2020 releases don't have data organized the same way
    if int(selected_release) < 20200101:
        return 
    
    # Post-2020 releases
    title = "Strain Issues"
    strain_listing_issues = query_strains(release=selected_release, issues=True)
    RELEASES = config["RELEASES"]
    DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == selected_release, RELEASES))[0]
    return render_template('strain_issues.html', **locals())

# =================== #
#   Download Script   #
# =================== #
@data_bp.route('/release/<string:selected_release>/download/download_isotype_bams.sh')
@jwt_required()
def download_script(selected_release):
  script_content = generate_bam_download_script(release=selected_release)
  download_page = render_template('download_script.sh', **locals())
  response = make_response(download_page)
  response.headers["Content-Type"] = "text/plain"
  return response


@data_bp.route('/release/latest/download/download_strain_bams.sh')
@data_bp.route('/release/<string:selected_release>/download/download_strain_bams.sh')
@jwt_required()
def download_script_strain_v2(selected_release=None):
  if selected_release is None:
      selected_release = config['DATASET_RELEASE']
  script_content = generate_bam_download_script(release=selected_release)
  download_page = render_template('download_script.sh', **locals())
  response = make_response(download_page)
  response.headers["Content-Type"] = "text/plain"
  return response


@data_bp.route('/download/files/<string:blob_name>')
@jwt_required()
def download_bam_url(blob_name=''):
  title = blob_name
  blob_path = 'bam/' + blob_name
  signed_download_url = generate_download_signed_url_v4(blob_path)
  return render_template('download.html', **locals())


def generate_bam_download_script(release):
  ''' Generates signed downloads urls for every sequenced strain and creates a script to download them ''' 
  script_content = ''
  expiration = timedelta(days=7)
  strain_listing = query_strains(release=release, is_sequenced=True)
  for strain in strain_listing:
    bam_path = 'bam/{}.bam'.format(strain)
    bai_path = 'bam/{}.bam.bai'.format(strain)
    script_content += '\n\n# Strain: {}'.format(strain)
    script_content += '\nwget "{}"'.format(generate_download_signed_url_v4(bam_path, expiration=expiration))
    script_content += '\nwget "{}"'.format(generate_download_signed_url_v4(bai_path, expiration=expiration))
  return script_content


# ============= #
#   Browser     #
# ============= #

@data_bp.route('/browser')
@data_bp.route('/browser/<int:release>')
@data_bp.route('/browser/<int:release>/<region>')
@data_bp.route('/browser/<int:release>/<region>/<query>')
def browser(release=config["DATASET_RELEASE"], region="III:11746923-11750250", query=None):
    VARS = {'title': "Variant Browser",
            'DATASET_RELEASE': int(release),
            'strain_listing': get_isotypes(),
            'region': region,
            'query': query,
            'fluid_container': True}
    return render_template('browser.html', **VARS)
