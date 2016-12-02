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

import string
import random

def id_generator(size = 4, chars = string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))

from google.appengine.api import taskqueue

def create_mapping_instance(report_slug, trait_slug):
    from oauth2client.client import GoogleCredentials
    credentials = GoogleCredentials.get_application_default()
    from googleapiclient import discovery
    compute = discovery.build('compute', 'v1', credentials=credentials)

    # Get latest CeNDR mapping image
    image_response = compute.images().getFromFamily(project='andersen-lab',
                                                     family = 'cendr').execute()
    source_disk_image = image_response['selfLink']

    #startup_script = open(
    #    os.path.join(
    #        os.path.dirname(__file__), 'startup-script.sh'), 'r').read()
    startup_script = '#! /bin/bash\n\nsleep 10s && gcloud -q compute instances delete --zone=us-central1-a `hostname`'

    config = {
        'name': 'cendr-mapping-submission-' + id_generator(4),
        'zone': 'projects/andersen-lab/zones/us-central1-a',
        'machineType': "zones/us-central1-a/machineTypes/n1-standard-1",
        'tags': {
            "items": ['cendr-mapping']
        },
        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                    'diskType': "projects/andersen-lab/zones/us-central1-a/diskTypes/pd-standard",
                    'diskSizeGb': "10"
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'projects/andersen-lab/global/networks/default',
            'accessConfigs': [
                {
                  "name": "External NAT",
                  "type": "ONE_TO_ONE_NAT"
                }
              ]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'andersen-lab@appspot.gserviceaccount.com',
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write',
                'https://www.googleapis.com/auth/compute'
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [{
                # Startup script is automatically executed by the
                # instance upon startup.
                'key': 'startup-script',
                'value': startup_script
            },  {
                'key': 'report_slug',
                'value': report_slug
            },
                {
            'key': 'trait_slug',
            'value': trait_slug 
            }]
        }
    }

    return compute.instances().insert(
        project='andersen-lab',
        zone='us-central1-a',
        body=config).execute()


@app.route("/launch_instance", methods=['POST'])
def task_test():
    print "Great"

def create_task():
    task = taskqueue.add(queue_name = 'map-queue', url='/launch_instance')
    #queue = taskqueue.Queue(name='map-queue')
    #queue.add_async(task)


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

def sortedfiles(path):
    return sorted([x for x in os.listdir(path) if not x.startswith(".")], reverse = True)

@app.route('/')
@cache.cached(timeout=50)
def main():
    page_title = "Caenorhabditis elegans Natural Diversity Resource"
    files = sortedfiles("cendr/static/content/news/")
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
    files = sortedfiles("cendr/static/content/news/")
    #sorts the thing in the right order on the webpage after clicking on the server
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
    files = sortedfiles("cendr/static/content/news/") #files is a list of file names
    # tuple_files=[]
    # for filename in files:
    #    tuple1=(datetime.strptime(filename[:10], "%Y-%m-%d"), filename[11:].strip(".md").replace("-", " "), filename)
    #    if len(tuple_files)==0:
    #        tuple_files.append(tuple1)
    #    else:
    #        for i in range(len(tuple_files)):
    #            if tuple1>tuple_files[i]:
    #                tuple_files.insert(i, tuple1)
    #            elif i==len(tuple_files):
    #                tuple_files.append(tuple1)

    # for filename in tuple_files:
    #    title = filename[1]
    #    content = render_markdown(filename[2].strip(".md"), "cendr/static/content/news/")
    #    date_published = filename[0]
    #    feed.add(title, unicode(content),
    #             content_type='html',
    #             author="CeNDR News",
    #             url=make_external(
    #                 url_for("news_item", filename=filename[2].strip(".md"))),
    #             updated=date_published,
    #             published=date_published)
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
