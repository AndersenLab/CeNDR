import os
import csv
import folium
import logging
from flask import render_template
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
import sys

app = Flask(__name__)

@app.route('/')
def main():
    title = "Cegwas"
    return render_template('home.html', **locals())

def data(text_file):
  with open(text_file, 'rU') as tsvin, open(text_file.rpartition('.')[0]+"_new.tsv", 'wb') as tsvout:
    tsvin = csv.reader(tsvin, delimiter='\t')
    count = 0
    arr = []
    elegans_map = folium.Map(location=[45.5236, -122.6750], tiles = 'Stamen Terrain')
    elegans_map.create_map(path='home.html')
    app.logger.info(elegans_map)
    for row in tsvin:
      if count == 0:
        app.logger.info(row)
        count += 1

      if count > 0:
          arr.append(row)
          elegans_map.simple_marker([row[1], row[2]], popup='Strain: {row[0]}, Isolation: {row[3]}, Location: {row[4]}')


    return arr

@app.route('/map/')
def map():
    title = "Map"
    data1 = data('strains/processed/strain_info.tsv')
    return render_template('home.html',
      **locals())

            # tsvot.writerows([fixed_row])

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug=True
    app.config['SECRET_KEY'] = '<123>'
    toolbar = DebugToolbarExtension(app)
    app.run(host='0.0.0.0', port=port)