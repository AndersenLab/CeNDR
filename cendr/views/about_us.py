from cendr import app, json_serial, cache
from flask import render_template, url_for, Markup
import markdown
import yaml
import json
from cendr.models import strain, report, mapping, trait
from collections import OrderedDict

@app.context_processor
def utility_processor():
    def render_markdown(filename, directory="cendr/static/content/markdown/"):
        with open(directory + filename) as f:
            return Markup(markdown.markdown(f.read()))
    return dict(render_markdown=render_markdown)


@app.route('/about/')
@cache.cached()
def about():
	# About us Page - directs to other pages.
    title = "About"
    bcs = OrderedDict([("about", None)])
    strain_listing = list(strain.select().filter(strain.isotype.is_null() == False)
        .filter(strain.latitude.is_null() == False).execute())
    strain_listing = json.dumps([x.__dict__["_data"] for x in strain_listing], default=json_serial)
    return render_template('about.html', **locals())



@app.route('/about/panel/')
@cache.cached()
def panel():
	# Scientific Panel Page
    title = "Scientific Advisory Panel"
    bcs = OrderedDict([("about", url_for("about")), ("panel", "")])
    panel_data = yaml.load(open("cendr/static/content/data/advisory-panel.yaml", 'r'))
    return render_template('panel.html', **locals())


@app.route('/about/staff/')
@cache.cached()
def staff():
	# Staff Page
    title = "Staff"
    bcs = OrderedDict([("about", url_for("about") ), ("staff", "")])
    staff_data = yaml.load(open("cendr/static/content/data/staff.yaml", 'r'))
    return render_template('staff.html', **locals())



@app.route('/about/statistics/')
@cache.cached()
def statistics():
    title = "Site Statistics"
    bcs = OrderedDict([("about", url_for("about")), ("statistics", None)])

    # Number of reports
    n_reports = report.select().count()
    n_traits = trait.select().count()
    n_significant_mappings = mapping.select().count()
    n_distinct_strains = strain.select(strain.strain).distinct().count()
    n_distinct_isotypes = strain.select(strain.isotype).filter(strain.isotype != None).distinct().count()

    # Collection dates
    collection_dates = list(strain.select().filter(
        strain.isotype != None, strain.isolation_date != None).order_by(strain.isolation_date).execute())

    return render_template('statistics.html', **locals())

