import os
import csv
import logging
from flask import render_template, request, send_from_directory, url_for, request
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
import sys
from cyvcf2 import VCF

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
    return render_template('gwa.html', **locals())


@app.route('/process_gwa/', methods=['POST'])
def process_gwa():
    title = "Run Association"
    req = request.get_json()
    print req
    return 'success'

@app.route("/report/<name>/")
def report(name):
    title = name
    return name

@app.route('/strain/<strain_name>/')
def strain(strain_name):
    title = strain_name
    print(strain_name)
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
