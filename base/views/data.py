import requests
from simplejson.errors import JSONDecodeError
from flask import make_response
from flask import render_template
from flask import Blueprint
from base.views.api.api_strain import get_isotypes, query_strains
from base.config import config
from base.models import Strain
from base.utils.gcloud import list_release_files

data_bp = Blueprint('data',
                    __name__,
                    template_folder='data')

# ============= #
#   Data Page   #
# ============= #
@data_bp.route('/release/latest')
@data_bp.route('/release/<string:selected_release>')
@data_bp.route('/release/<string:selected_release>')
def data(selected_release=config["DATASET_RELEASE"]):
    """
        Default data page - lists
        available releases.
    """
    # Pre-2020 releases used BAMs grouped by isotype.
    if int(selected_release) < 20200101:
        return data_v01(selected_release)
    
    # Post-2020 releases keep strain-level bams separate.
    title = "Releases"
    sub_page = selected_release
    strain_listing = query_strains(release=selected_release)
    release_summary = Strain.release_summary(selected_release)
    RELEASES = config["RELEASES"]
    DATASET_RELEASE, WORMBASE_VERSION = list(filter(lambda x: x[0] == selected_release, RELEASES))[0]
    REPORTS = ["alignment"]
    return render_template('data_v2.html', **locals())


def data_v01(selected_release):
    # Legacy releases (Pre 20200101)
    title = "Releases"
    subtitle = selected_release
    strain_listing = query_strains(release=selected_release)
    # Fetch variant data
    url = "https://storage.googleapis.com/elegansvariation.org/releases/{selected_release}/multiqc_bcftools_stats.json".format(selected_release=selected_release)
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


# =================== #
#   Download Script   #
# =================== #

@data_bp.route('/download/download_isotype_bams.sh')
def download_script():
    strain_listing = query_strains(release=config["DATASET_RELEASE"])
    download_page = render_template('download_script.sh', **locals())
    response = make_response(download_page)
    response.headers["Content-Type"] = "text/plain"
    return response

@data_bp.route('/download/download_strain_bams.sh')
def download_script_strain_v2():
    v2 = True
    strain_listing = query_strains(release=config["DATASET_RELEASE"])
    download_page = render_template('download_script.sh', **locals())
    response = make_response(download_page)
    response.headers["Content-Type"] = "text/plain"
    return response


# ============= #
#   Browser     #
# ============= #

@data_bp.route('/browser')
@data_bp.route('/browser/<string:release>')
@data_bp.route('/browser/<string:release>/<region>')
@data_bp.route('/browser/<string:release>/<region>/<query>')
def browser(release=config["DATASET_RELEASE"], region="III:11746923-11750250", query=None):
    VARS = {'title': "Variant Browser",
            'DATASET_RELEASE': release,
            'isotype_listing': get_isotypes(list_only=True),
            'region': region,
            'query': query,
            'fluid_container': True}
    return render_template('browser.html', **VARS)
