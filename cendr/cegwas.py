from cendr import app, cache
from models import trait, report
from flask import render_template, request, Markup, url_for, Response, redirect
import markdown
from datetime import datetime
import os
from collections import OrderedDict
import dateutil
from werkzeug.contrib.atom import AtomFeed
from urlparse import urljoin

def make_external(url):
    return urljoin(request.url_root, url)


def render_markdown(filename, directory="cendr/static/content/markdown/"):
    with open(directory + filename + ".md") as f:
        return Markup(markdown.markdown(f.read()))


@app.template_filter('format_datetime')
def format_datetime(value):
    try:
        return dateutil.parser.parse(value).strftime('%Y-%m-%d / %I:%M %p')
    except:
        pass


@app.route('/')
@cache.cached(timeout=50)
def main():
    page_title = "Caenorhabditis elegans Natural Diversity Resource"
    files = [x for x in os.listdir("cendr/static/content/news/") if not x.startswith(".")]
    files.reverse()
    # latest mappings
    latest_mappings = list(report.filter(report.release == 0, trait.status == "complete").join(trait).order_by(
        trait.submission_complete.desc()).limit(5).select(report, trait).distinct().dicts().execute())
    return render_template('home.html', **locals())

@app.route("/.well-known/acme-challenge/")
def le():
    code = ""
    return Response(code, mimetype = "text/plain")

@app.route("/.well-known/acme-challenge/")
def le2():
    code = ""
    return Response(code, mimetype = "text/plain")


@app.route("/Software")
def reroute_software():
    return redirect(url_for('help_item', filename = "Software"))

@app.route("/news/")
@app.route("/news/<filename>/")
@cache.memoize(50)
def news_item(filename = ""):
    files = [x for x in os.listdir("cendr/static/content/news/") if not x.startswith(".")]
    files.reverse()
    if not filename:
        filename = files[0].strip(".md")
    title = filename[11:].strip(".md").replace("-", " ")
    bcs = OrderedDict([("News", None), (title, None)])
    return render_template('news_item.html', **locals())


@app.route("/help/")
@app.route("/help/<filename>/")
@cache.memoize(50)
def help_item(filename = ""):
    files = ["FAQ", "Variant-Browser", "Variant-Prediction", "Methods", "Software", "Change-Log"]
    if not filename:
        filename = "FAQ"
    title = filename.replace("-", " ")
    bcs = OrderedDict([("Help","/help"), (title, None)])
    return render_template('help_item.html', **locals())


@app.route('/feed.atom')
def feed():
    feed = AtomFeed('CeNDR News',
                    feed_url=request.url, url=request.url_root)
    files = os.listdir("cendr/static/content/news/")
    for filename in files:
        title = filename[11:].strip(".md").replace("-", " ")
        content = render_markdown(filename.strip(".md"), "cendr/static/content/news/")
        date_published = datetime.strptime(filename[:10], "%Y-%m-%d")
        feed.add(title, unicode(content),
                 content_type='html',
                 author="CeNDR News",
                 url=make_external(
                     url_for("news_item", filename=filename.strip(".md"))),
                 updated=date_published,
                 published=date_published)
    return feed.get_response()


@app.route('/outreach/')
@cache.cached()
def outreach():
    title = "Outreach"
    bcs = OrderedDict([("Outreach", "")])
    return render_template('outreach.html', **locals())



@app.route('/contact-us/')
@cache.cached()
def contact():
    title = "Contact Us"
    bcs = OrderedDict([("Contact", None)])
    return render_template('contact.html', **locals())


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
