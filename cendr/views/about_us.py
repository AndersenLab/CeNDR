from cendr import app
from flask import render_template
from flask import Markup
import markdown
import yaml
from cendr.models import strain, report
from collections import OrderedDict

@app.context_processor
def utility_processor():
    def render_markdown(filename, directory="cendr/static/content/markdown/"):
        with open(directory + filename) as f:
            return Markup(markdown.markdown(f.read()))
    return dict(render_markdown=render_markdown)


@app.route('/about/')
def about():
	# About us Page - directs to other pages.
    title = "About"
    bcs = OrderedDict([("about", "/about/")])
    return render_template('about.html', **locals())


@app.route('/about/panel/')
def panel():
	# Scientific Panel Page
    title = "Scientific Advisory Panel"
    bcs = OrderedDict([("about", "/about/"), ("panel", "")])
    panel_data = yaml.load(open("cendr/static/content/data/advisory-panel.yaml", 'r'))
    return render_template('panel.html', **locals())


@app.route('/about/staff/')
def staff():
	# Staff Page
    title = "Staff"
    bcs = OrderedDict([("about", "/about/"), ("staff", "")])
    staff_data = yaml.load(open("cendr/static/content/data/staff.yaml", 'r'))
    return render_template('staff.html', **locals())


@app.route('/about/statistics/')
def statistics():
    title = "Site Statistics"
    bcs = OrderedDict([("about", "/about/"), ("statistics", None)])

    # Collection dates
    collection_dates = list(strain.select().filter(
        strain.isotype != None, strain.isolation_date != None).order_by(strain.isolation_date).execute())

    return render_template('statistics.html', **locals())

