import os
import markdown
import dateutil
from base.application import app, cache, get_ds
from base.models import trait, report
from flask import render_template, request, Markup, url_for, Response, redirect
from datetime import datetime
from collections import OrderedDict
from werkzeug.contrib.atom import AtomFeed
from urllib.parse import urljoin


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

@app.template_filter('format_datetime')
def format_datetime(value):
    try:
        return dateutil.parser.parse(value).strftime('%Y-%m-%d / %I:%M %p')
    except:
        pass

@app.template_filter('dump')
def show_all_attrs(value):
    res = []
    for k in dir(value):
        res.append('%r - %r\n<br>' % (k, getattr(value, k)))
    return '\n'.join(res)

def sortedfiles(path):
    return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse = True)

