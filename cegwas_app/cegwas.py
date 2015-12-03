import os
import csv
import folium
import logging
from flask import render_template
from flask import Flask
from flask_debugtoolbar import DebugToolbarExtension
import pandas as pd
import sys

app = Flask(__name__)

@app.route('/')
def main():
    title = "Cegwas"
    return render_template('home.html', **locals())

def data():
  # with open(text_file, 'rU') as tsvin, open(text_file.rpartition('.')[0]+"_new.tsv", 'wb') as tsvout:
  #   tsvin = csv.reader(tsvin, delimiter='\t')
  countries_geo = r'/countries.json'
  c_elegans= r'strains/processed/strain_info.tsv'

  c_elegans_data = pd.read_csv(c_elegans, sep='\t')

  map = folium.Map(location=[48, -102], zoom_start=3)
  map.geo_json(geo_path=countries_geo, data=c_elegans_data,
             columns=['strain','longitude','latitude'],
             key_on='feature.id',
             fill_color='YlGn', fill_opacity=0.7, line_opacity=0.2,
             legend_name='Strains')
  map.create_map(path='map.html')
  # count = 0
  # arr = []

  # for row in tsvin:
  #   if count == 0:
  #     app.logger.info(row)
  #     count += 1

  #   if count > 0:
  #       arr.append(row)
  #       elegans_map.simple_marker([row[1], row[2]], popup='Strain: {row[0]}, Isolation: {row[3]}, Location: {row[4]}')


  return c_elegans_data

@app.route('/map/')
def map():
    title = "Map"
    data()
    return render_template('map.html',
      **locals())

            # tsvot.writerows([fixed_row])

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 5000))
    app.debug=True
    app.config['SECRET_KEY'] = '<123>'
    toolbar = DebugToolbarExtension(app)
    app.run(host='0.0.0.0', port=port)