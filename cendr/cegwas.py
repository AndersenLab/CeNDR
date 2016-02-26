from cendr import app
from models import trait, report
from flask import render_template
import os
import dateutil
from werkzeug.contrib.atom import AtomFeed

def make_external(url):
    return urljoin(request.url_root, url)


def render_markdown(filename, directory="static/content/markdown/"):
    with open(directory + filename) as f:
        return Markup(markdown.markdown(f.read()))


@app.template_filter('format_datetime')
def format_datetime(value):
    try:
        return dateutil.parser.parse(value).strftime('%Y-%m-%d / %I:%M %p')
    except:
        pass


@app.route('/')
def main():
    page_title = "Caenorhabditis elegans Natural Diversity Resource"
    files = [x for x in os.listdir(
        "cendr/static/content/news/") if x.startswith(".") is False]
    files.reverse()
    # latest mappings
    latest_mappings = list(report.filter(report.release == 0).join(trait).order_by(
        trait.submission_complete.desc()).limit(5).select(report, trait).distinct().dicts().execute())
    return render_template('home.html', **locals())


@app.route("/news/")
def news():
    title = "Andersen Lab News"
    files = os.listdir("static/content/news/")
    files.reverse()
    bcs = OrderedDict([("News", "")])
    return render_template('news.html', **locals())


@app.route("/news/<filename>/")
def news_item(filename):
    title = filename[11:].strip(".md").replace("-", " ")
    return render_template('news_item.html', **locals())


@app.route('/feed.atom')
def feed():
    feed = AtomFeed('CNDR News',
                    feed_url=request.url, url=request.url_root)
    files = os.listdir("static/content/news/")
    files.reverse()
    for filename in files:
        filename[11:]
        title = filename[11:].strip(".md").replace("-", " ")
        content = render_markdown(filename, "static/content/news/")
        date_published = datetime.strptime(filename[:10], "%Y-%m-%d")
        feed.add(title, unicode(content),
                 content_type='html',
                 author="CNDR News",
                 url=make_external(
                     url_for("news_item", filename=filename.strip(".md"))),
                 updated=date_published,
                 published=date_published)
    return feed.get_response()


@app.route('/outreach/')
def outreach():
    title = "Outreach"
    bcs = OrderedDict([("outreach", "")])
    return render_template('outreach.html', **locals())


@app.route('/contact-us/')
def contact():
    title = "Contact Us"
    bcs = OrderedDict([("Contact Us", "/contact-us/")])
    return render_template('contact.html', **locals())


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
