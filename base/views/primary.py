from base.application import app, json_serial, cache, get_ds, add_to_order_ws, send_mail
from flask import render_template, url_for, Markup, request, redirect
import os
from base.models import strain, report, mapping, trait
from base.emails import donate_submission
from base.utils.data import load_yaml
from collections import OrderedDict
from datetime import datetime
import pytz
import hashlib
from requests import post
from flask import Blueprint

primary_bp = Blueprint('primary',
                    __name__,
                    template_folder='primary')


def sortedfiles(path):
    return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse = True)

# Homepage
@primary_bp.route('/')
@cache.cached(timeout=50)
def main():
    title = "Caenorhabditis elegans Natural Diversity Resource"
    files = sortedfiles("base/static/content/news/")
    #latest_mappings = list(report.filter(report.release == 0, trait.status == "complete").join(trait).order_by(
    #    trait.submission_complete.desc()).limit(5).select(report, trait).distinct().dicts().execute())
    return render_template('home.html', **locals())




@primary_bp.route("/.well-known/acme-challenge/<acme>")
def le(acme):
    ds = get_ds()
    try:
        acme_challenge = ds.get(ds.key("credential", acme))
        return Response(acme_challenge['token'], mimetype = "text/plain")
    except:
        return Response("Error", mimetype = "text/plain")


@primary_bp.route("/Software")
def reroute_software():
    return redirect(url_for('help_item', filename = "Software"))

@primary_bp.route("/news/")
@primary_bp.route("/news/<filename>/")
def news_item(filename = ""):
    files = sortedfiles("cendr/static/content/news/")
    #sorts the thing in the right order on the webpage after clicking on the server
    if not filename:
        filename = files[0].strip(".md")
    title = filename[11:].strip(".md").replace("-", " ")
    return render_template('news_item.html', **locals())


@primary_bp.route("/help/")
@primary_bp.route("/help/<filename>/")
def help_item(filename = ""):
    files = ["FAQ", "Variant-Browser", "Variant-Prediction", "Methods", "Software", "Change-Log"]
    if not filename:
        filename = "FAQ"
    title = filename.replace("-", " ")
    return render_template('help_item.html', **locals())


@primary_bp.route('/feed.atom')
def feed():
    feed = AtomFeed('CeNDR News',
                    feed_url=request.url, url=request.url_root)
    files = sortedfiles("cendr/static/content/news/") #files is a list of file names
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
def outreach():
    title = "Outreach"
    return render_template('outreach.html', **locals())




@primary_bp.route('/contact-us/')
def contact():
    title = "Contact Us"
    return render_template('contact.html', **locals())


@primary_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@primary_bp.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
