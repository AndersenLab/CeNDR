from base.application import cache
from flask import render_template, url_for, request, redirect
import os
from datetime import datetime
from flask import Blueprint

primary_bp = Blueprint('primary',
                       __name__)


def sortedfiles(path):
    return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse=True)


# Homepage
@primary_bp.route('/')
@cache.cached(timeout=50)
def main():
    page_title = "Caenorhabditis elegans Natural Diversity Resource"
    files = sortedfiles("base/static/content/news/")
    #latest_mappings = list(report.filter(report.release == 0, trait.status == "complete").join(trait).order_by(
    #    trait.submission_complete.desc()).limit(5).select(report, trait).distinct().dicts().execute())
    return render_template('primary/home.html', **locals())


@primary_bp.route("/Software")
def reroute_software():
    # This is a redirect due to a typo in the original CeNDR manuscript. Leave it.
    return redirect(url_for('help_item', filename="Software"))


@primary_bp.route("/news/")
@primary_bp.route("/news/<filename>/")
def news_item(filename=""):
    files = sortedfiles("cendr/static/content/news/")
    # sorts the thing in the right order on the webpage 
    # after clicking on the server
    if not filename:
        filename = files[0].strip(".md")
    title = filename[11:].strip(".md").replace("-", " ")
    return render_template('news_item.html', **locals())


@primary_bp.route("/help/")
@primary_bp.route("/help/<filename>/")
def help_item(filename=""):
    files = ["FAQ", "Variant-Browser", "Variant-Prediction", "Methods", "Software", "Change-Log"]
    if not filename:
        filename = "FAQ"
    title = filename.replace("-", " ")
    return render_template('help_item.html', **locals())


@primary_bp.route('/feed.atom')
def feed():
    feed = AtomFeed('CeNDR News',
                    feed_url=request.url, url=request.url_root)
    files = sortedfiles("cendr/static/content/news/")  # files is a list of file names
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


@primary_bp.route('/outreach/')
@cache.cached(timeout=50)
def outreach():
    title = "Outreach"
    return render_template('outreach.html', **locals())


@primary_bp.route('/contact-us/')
@cache.cached(timeout=50)
def contact():
    title = "Contact Us"
    return render_template('contact.html', **locals())


@primary_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@primary_bp.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500