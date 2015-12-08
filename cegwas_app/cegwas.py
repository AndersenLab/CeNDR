import os
import csv
import folium
import logging
from flask import render_template,request,send_from_directory
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
import pandas as pd
import sys

app = Flask(__name__)

@app.route('/')
def main():
    title = "Cegwas"
    return render_template('home.html', **locals())


@app.route('/map/')
def map():
    title = "Map"
    return render_template('map.html',
      **locals())

@app.route('/strain_info.tsv')
def strain_locations():
    title = "Locations"
    # return send_from_directory(app.static_folder,request.path[1:], as_attachment=False)

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug=True
    app.config['SECRET_KEY'] = '<123>'
    toolbar = DebugToolbarExtension(app)
    app.run(host='0.0.0.0', port=port)