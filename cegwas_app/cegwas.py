import os
import csv
import logging
from flask import render_template, request, send_from_directory, url_for, request
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
import sys
from cyvcf2 import VCF
from slugify import slugify
import hashlib
import IPython
from models import *


app = Flask(__name__, static_url_path='/static')

@app.route('/')
def main():
    title = "Cegwas"
    return render_template('home.html', **locals())


@app.route('/map/')
def map():
    title = "Map"
    return render_template('map.html', **locals())


@app.route('/gwa/')
def gwa():
    title = "Run Association"

    strain_list = json.dumps([x.strain for x in strain.select(strain.strain).filter(strain.isotype.is_null() == False).execute()])
    print(strain_list)
    return render_template('gwa.html', **locals())


@app.route('/process_gwa/', methods=['POST'])
def process_gwa():
    title = "Run Association"
    req = request.get_json()
    print req
    return 'success'


@app.route('/validate_url/', methods=['POST'])
def validate_url():
    """
        Generates URLs from report names and validates them.
    """
    req = request.get_json()

    # [ ] - Add Code to check against database that report (slug) is not already taken.

    report_out = slugify(req["report_name"])
    if req["release"] != "public":
        report_out = str(hashlib.sha224(req["report_name"]).hexdigest()[0:20])
    if len(req["report_name"]) > 40:
        return json.dumps({'error': "Report name may not be > 40 characters."})
    else:
        return json.dumps({'report_name': report_out})


@app.route("/report/<name>/")
def report(name):
    title = name
    return name


@app.route('/strain/')
def strain_listing_page():
    title = "Strain List"
    strain_listing = strain.select().filter(strain.isotype != None).order_by(strain.isotype).execute()
    return render_template('strain_listing.html', **locals())


# [ ] - change URL schema to be "/isotype/strain/"; Use url-for!
# [ ] - Add breadcrumbs to strain page.
# [ ] - Highlight isotype using ?=isotype get param

@app.route('/strain/<strain_name>/')
def strain_page(strain_name):
    title = strain_name
    strain_isotype = strain.get(strain.strain == strain_name).isotype
    return render_template('strain.html', **locals())


@app.route('/variants/<chrom>/<start>/<end>/')
def variants(chrom, start, end):
    vcf = VCF("static/vcf/union_merged.vcf.gz")
    region = "{chrom}:{start}-{end}".format(**locals())
    for var in vcf(region):
        x = var
    return dict(x)



if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug=True
    app.config['SECRET_KEY'] = '<123>'
    toolbar = DebugToolbarExtension(app)
    app.run(host='0.0.0.0', port=port)

