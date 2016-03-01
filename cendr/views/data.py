from cendr import app
from flask import make_response
from cendr.models import strain, report
from collections import OrderedDict
from flask import render_template


@app.route('/data/')
def data_page():
    bcs = OrderedDict([("data", None)])
    title = "Data"
    current_variant_set = "20160106"
    strain_listing = strain.select().filter(
        strain.isotype != None).order_by(strain.isotype).execute()
    return render_template('data.html', **locals())


@app.route('/data/browser')
def genome_browser():
    bcs = OrderedDict([("data", 'Browser')])
    title = "Browser"
    return render_template('browser.html', **locals())


@app.route('/data/download/<filetype>.sh')
def download_script(filetype):
    strain_listing = strain.select().filter(
        strain.isotype != None).order_by(strain.isotype).execute()
    download_page = render_template('download_script.sh', **locals())
    response = make_response(download_page)
    response.headers["Content-Type"] = "text/plain"
    return response
