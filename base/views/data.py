import requests
from flask import make_response
from flask import render_template
from flask import Blueprint
from base.views.api.api_strain import get_isotypes, query_strains
from base.constants import DATASET_RELEASE, RELEASES
from base.models2 import strain_m


data_bp = Blueprint('data',
                    __name__,
                    template_folder='data')


#
# Data Page
#

@data_bp.route('/release/latest')
@data_bp.route('/release/<string:selected_release>')
@data_bp.route('/release/<string:selected_release>')
def data(selected_release=DATASET_RELEASE):
    """
        Default data page - lists
        available releases.
    """
    title = "Releases"
    strain_listing = query_strains(release=selected_release)
    # Fetch variant data
    url = "https://storage.googleapis.com/elegansvariation.org/releases/{selected_release}/multiqc_bcftools_stats.json".format(selected_release=selected_release)
    vcf_summary = requests.get(url).json()
    release_summary = strain_m.release_summary(selected_release)
    VARS = {'title': title,
            'strain_listing': strain_listing,
            'vcf_summary': vcf_summary,
            'RELEASES': RELEASES,
            'release_summary': release_summary,
            'selected_release': selected_release,
            'wormbase_genome_version': dict(RELEASES)[selected_release]}
    return render_template('data.html', **VARS)


#
# Download Script
#

@data_bp.route('/download/download_bams.sh')
def download_script():
    strain_listing = query_strains(release=DATASET_RELEASE)
    download_page = render_template('download_script.sh', **locals())
    response = make_response(download_page)
    response.headers["Content-Type"] = "text/plain"
    return response

#
# Browser
#

@data_bp.route('/browser/')
@data_bp.route('/browser/<region>')
@data_bp.route('/browser/<region>/<query>')
def browser(region="III:11746923-11750250", query=None):
    VARS = {'title': "Genome Browser",
            'DATASET_RELEASE': DATASET_RELEASE,
            'isotype_listing': get_isotypes(list_only=True),
            'region': region,
            'query': query,
            'fluid_container': True}
    return render_template('browser.html', **VARS)
