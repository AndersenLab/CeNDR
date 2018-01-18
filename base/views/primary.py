#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import os
from flask import render_template, url_for, request, redirect, Blueprint, session
from base.utils.text_utils import render_markdown
from base.utils.data_utils import sorted_files
from datetime import datetime
from urllib.parse import urljoin
from werkzeug.contrib.atom import AtomFeed


primary_bp = Blueprint('primary',
                       __name__)

# Homepage
@primary_bp.route('/')
def primary():
    page_title = "Caenorhabditis elegans Natural Diversity Resource"
    files = sorted_files("base/static/content/news/")
    VARS = {'page_title': page_title,
            'files': files}
    #latest_mappings = list(report.filter(report.release == 0, trait.status == "complete").join(trait).order_by(
    #    trait.submission_complete.desc()).limit(5).select(report, trait).distinct().dicts().execute())
    return render_template('primary/home.html', **VARS)


@primary_bp.route("/Software")
def reroute_software():
    # This is a redirect due to a typo in the original CeNDR manuscript. Leave it.
    return redirect(url_for('help_item', filename="Software"))


@primary_bp.route("/news/")
@primary_bp.route("/news/<filename>/")
def news_item(filename=""):
    files = sorted_files("base/static/content/news/")
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
    """
        This view renders the sites ATOM feed.
    """
    feed = AtomFeed('CeNDR News',
                    feed_url=request.url, url=request.url_root)
    files = sorted_files("base/static/content/news/")  # files is a list of file names
    for filename in files:
        title = filename[11:].strip(".md").replace("-", " ")
        content = render_markdown(filename, "base/static/content/news/")
        date_published = datetime.strptime(filename[:10], "%Y-%m-%d")
        feed.add(title, content,
                 content_type='html',
                 author="CeNDR News",
                 url=urljoin(request.url_root, url_for("primary.news_item", filename=filename.strip(".md"))),
                 updated=date_published,
                 published=date_published)
    return feed.get_response()


@primary_bp.route('/outreach/')
def outreach():
    title = "Outreach"
    return render_template('primary/outreach.html', **locals())


@primary_bp.route('/contact-us/')
def contact():
    title = "Contact Us"
    return render_template('contact.html', **locals())

