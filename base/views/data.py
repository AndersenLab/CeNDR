import requests
import os

from datetime import timedelta
from simplejson.errors import JSONDecodeError
from flask import make_response, render_template, Blueprint, send_file

from base.constants import BAM_BAI_DOWNLOAD_SCRIPT_NAME, GOOGLE_CLOUD_BUCKET
from base.config import config
from base.extensions import cache
from base.models import Strain
from base.utils.gcloud import list_release_files, generate_download_signed_url_v4, download_file
from base.utils.jwt_utils import jwt_required
from base.views.api.api_strain import get_isotypes, query_strains


data_bp = Blueprint('data',
                    __name__,
                    template_folder='data')

# ============= #
#   Data Page   #
# ============= #

@cache.memoize(50)
def generate_v2_file_list(selected_release):
  path = f'releases/{selected_release}'
  prefix = f'https://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/{path}'
  release_files = list_release_files(f"{path}/")
  
  f = dict()

  f['soft_filter_vcf_gz'] = f'{prefix}/variation/WI.{selected_release}.soft-filter.vcf.gz'
  f['soft_filter_vcf_gz_csi'] = f'{prefix}/variation/WI.{selected_release}.soft-filter.vcf.gz.csi'
  f['soft_filter_isotype_vcf_gz'] = f'{prefix}/variation/WI.{selected_release}.soft-filter.isotype.vcf.gz'
  f['soft_filter_isotype_vcf_gz_csi'] = f'{prefix}/variation/WI.{selected_release}.soft-filter.isotype.vcf.gz.csi'
  f['hard_filter_vcf_gz'] = f'{prefix}/variation/WI.{selected_release}.hard-filter.vcf.gz'
  f['hard_filter_vcf_gz_csi'] = f'{prefix}/variation/WI.{selected_release}.hard-filter.vcf.gz.csi'
  f['hard_filter_isotype_vcf_gz'] = f'{prefix}/variation/WI.{selected_release}.hard-filter.isotype.vcf.gz'
  f['hard_filter_isotype_vcf_gz_csi'] = f'{prefix}/variation/WI.{selected_release}.hard-filter.isotype.vcf.gz.csi'
  f['impute_isotype_vcf_gz'] = f'{prefix}/variation/WI.{selected_release}.impute.isotype.vcf.gz'
  f['impute_isotype_vcf_gz_csi'] = f'{prefix}/variation/WI.{selected_release}.impute.isotype.vcf.gz.csi'
  
  f['hard_filter_min4_tree'] = f'{prefix}/tree/WI.{selected_release}.hard-filter.min4.tree'
  f['hard_filter_min4_tree_pdf'] = f'{prefix}/tree/WI.{selected_release}.hard-filter.min4.tree.pdf'
  f['hard_filter_isotype_min4_tree'] = f'{prefix}/tree/WI.{selected_release}.hard-filter.isotype.min4.tree'
  f['hard_filter_isotype_min4_tree_pdf'] = f'{prefix}/tree/WI.{selected_release}.hard-filter.isotype.min4.tree.pdf'
  
  f['haplotype_png'] = f'{prefix}/haplotype/haplotype.png'
  f['haplotype_pdf'] = f'{prefix}/haplotype/haplotype.pdf'
  f['sweep_pdf'] = f'{prefix}/haplotype/sweep.pdf'
  f['sweep_summary_tsv'] = f'{prefix}/haplotype/sweep_summary.tsv'

  for key, value in f.items():
    if value not in release_files:
      f[key] = None
  
  return f


@data_bp.route('/release/latest')
@data_bp.route('/release/<string:selected_release>')
@cache.memoize(50)
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
    f = generate_v2_file_list(selected_release)
    return render_template('data_v2.html', **locals())


@cache.memoize(50)
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
@cache.memoize(50)
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
@cache.memoize(50)
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
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script(selected_release):
  if not os.path.exists(BAM_BAI_DOWNLOAD_SCRIPT_NAME):
    download_file(f'bam/{BAM_BAI_DOWNLOAD_SCRIPT_NAME}', BAM_BAI_DOWNLOAD_SCRIPT_NAME)
  return send_file(BAM_BAI_DOWNLOAD_SCRIPT_NAME, as_attachment=True)



@data_bp.route('/release/latest/download/download_strain_bams.sh')
@data_bp.route('/release/<string:selected_release>/download/download_strain_bams.sh')
@cache.cached(timeout=60*60*24)
@jwt_required()
def download_script_strain_v2(selected_release=None):
  return send_file(BAM_BAI_DOWNLOAD_SCRIPT_NAME, as_attachment=True)


@data_bp.route('/download/files/<string:blob_name>')
@jwt_required()
def download_bam_url(blob_name=''):
  title = blob_name
  blob_path = 'bam/' + blob_name
  signed_download_url = generate_download_signed_url_v4(blob_path)
  msg = 'download will begin shortly...'
  if not signed_download_url:
    msg = 'error fetching download link'
    signed_download_url = ''

  return render_template('download.html', **locals())


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
            'fluid_container': False}
    return render_template('browser.html', **VARS)
