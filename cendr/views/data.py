from cendr import app
from cendr import api
from flask import make_response
from cendr.models import strain, report, homologene
from collections import OrderedDict
from flask import render_template


@app.route('/data/')
def data_page():
    bcs = OrderedDict([("Data", None)])
    title = "Data"
    from cendr import build
    strain_listing = strain.select().filter(
        strain.isotype != None).order_by(strain.isotype).execute()
    return render_template('data.html', **locals())


@app.route('/data/download/<filetype>.sh')
def download_script(filetype):
    strain_listing = strain.select().filter(
        strain.isotype != None).order_by(strain.isotype).execute()
    download_page = render_template('download_script.sh', **locals())
    response = make_response(download_page)
    response.headers["Content-Type"] = "text/plain"
    return response


@app.route('/data/browser/')
@app.route('/data/browser/<chrom>/<start>/<end>/')
@app.route('/data/browser/<chrom>/<start>/<end>/<tracks>')
def browser(chrom = "III", start = 11746923, end = 11750250, tracks="mh"):
    bcs = OrderedDict([("Data", "/data"), ("Browser", None)])
    title = "Browser"
    
    putative_impact = {'l': 'LOW', 'm':'MODERATE', 'h': 'HIGH'}
    var_eff = [putative_impact[x] if x else '' for x in tracks]
    putative_impact_items = putative_impact.items()
    
    from cendr import build
    
    isotype_listing = list(strain.select(strain.isotype).distinct().filter(
                                    strain.isotype != None).order_by(strain.isotype).dicts().execute())
    isotypes = [x["isotype"] for x in isotype_listing]
    
    return render_template('browser.html', **locals())