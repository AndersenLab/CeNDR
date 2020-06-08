#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import requests
import markdown
import pytz
from flask import Markup
from flask import render_template, url_for, request, redirect, Blueprint
from base.utils.text_utils import render_markdown
from base.utils.data_utils import sorted_files
from datetime import datetime
from urllib.parse import urljoin
from feedgen.feed import FeedGenerator
from base.utils.query import get_latest_public_mappings

primary_bp = Blueprint('primary',
                       __name__)


@primary_bp.route('/')
def primary():
    """
        The home page
    """
    page_title = "Caenorhabditis elegans Natural Diversity Resource"
    files = sorted_files("base/static/content/news/")
    VARS = {'page_title': page_title,
            'files': files,
            'latest_mappings': get_latest_public_mappings()}
    return render_template('primary/home.html', **VARS)


@primary_bp.route("/Software")
def reroute_software():
    # This is a redirect due to a typo in the original CeNDR manuscript. Leave it.
    return redirect(url_for('primary.help_item', filename="Software"))


@primary_bp.route("/news/")
@primary_bp.route("/news/<filename>/")
def news_item(filename=""):
    """
        News
    """
    files = sorted_files("base/static/content/news/")
    if not filename:
        filename = files[0].strip(".md")
    title = filename[11:].strip(".md").replace("-", " ")
    return render_template('news_item.html', **locals())



# @primary_bp.route("/special/")
# def dbx_help(filename=""):
#     """
#         Help
#     """
#     f = requests.get("https://dl.dropbox.com/s/al68jcsc8xc3yqo/faq.md?dl=1")
#     return Markup(markdown.markdown(f.text))


@primary_bp.route("/help/")
@primary_bp.route("/help/<filename>/")
def help_item(filename=""):
    """
        Help
    """
    files = ["FAQ", "Variant-Browser", "Variant-Prediction", "Methods", "Software", "Change-Log"]
    if not filename:
        filename = "FAQ"
    title = filename.replace("-", " ")
    return render_template('help_item.html', **locals())


@primary_bp.route('/feed.atom')
def feed():
    """
        This view renders the sites ATOM feed.
    """
    fg = FeedGenerator()

    fg.id("CeNDR.News")
    fg.title("CeNDR News")
    fg.author({'name':'CeNDR Admin','email':'erik.andersen@northwestern.edu'})
    fg.link( href='http://example.com', rel='alternate' )
    fg.logo('http://ex.com/logo.jpg')
    fg.subtitle('This is a cool feed!')
    fg.language('en')
    fg.link( href=request.url, rel='self' )
    fg.language('en')
    files = sorted_files("base/static/content/news/")  # files is a list of file names
    for filename in files:
        fe = fg.add_entry()
        fe.id(filename[11:].strip(".md").replace("-", " "))
        fe.title(filename[11:].strip(".md").replace("-", " "))
        fe.author({'name':'CeNDR Admin','email':'erik.andersen@northwestern.edu'})
        fe.link(href=urljoin(request.url_root, url_for("primary.news_item", filename=filename.strip(".md"))))
        fe.content(render_markdown(filename, "base/static/content/news/"))
        fe.pubDate(pytz.timezone("America/Chicago").localize(datetime.strptime(filename[:10], "%Y-%m-%d")))
    return fg.atom_str(pretty=True)


@primary_bp.route('/outreach/')
def outreach():
    title = "Outreach"
    return render_template('primary/outreach.html', **locals())


@primary_bp.route('/contact-us/')
def contact():
    title = "Contact Us"
    return render_template('contact.html', **locals())
