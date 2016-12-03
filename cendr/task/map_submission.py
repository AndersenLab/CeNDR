from cendr import app
from cendr.models import *
from flask import request
from google.appengine.api import taskqueue
import string
import random
from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
credentials = GoogleCredentials.get_application_default()
compute = discovery.build('compute', 'v1', credentials=credentials)
import time

def id_generator(size = 4, chars = string.ascii_lowercase):
    """
        Generate random 4 letter id.
    """
    return ''.join(random.choice(chars) for _ in range(size))

def create_mapping_instance(gce_name, params):
    # Get latest CeNDR mapping image
    image_response = compute.images().getFromFamily(project='andersen-lab',
                                                     family = 'cendr').execute()
    source_disk_image = image_response['selfLink']


    config = {
        'name': 'cendr-' + gce_name + "-" + id_generator(4),
        'zone': 'projects/andersen-lab/zones/us-central1-a',
        'machineType': "zones/us-central1-a/machineTypes/custom-1-6656",
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
                'https://www.googleapis.com/auth/cloud-platform'
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': params
        }
    }

    instance = compute.instances().insert(
        project='andersen-lab',
        zone='us-central1-a',
        body=config).execute()
    print(instance)
    return instance

def instance_count():
    print("invoked")
    instances = compute.instances().list(project='andersen-lab', zone = 'us-central1-a', filter='status eq RUNNING').execute()['items']
    mapping_instances = [x['name'] for x in instances if x['name'].startswith("cendr")]
    return len(mapping_instances)

@app.route("/launch_instance", methods=['POST'])
def launch_instance():
    try:
        params = [{'key':k, 'value': v} for k,v in request.form.items()]
        gce_name = request.form['report_slug'] + "-" + request.form['trait_slug']
        startup_script = open('cendr/task/startup-script.sh','r').read()
        run_pipeline = open('cendr/task/run_pipeline.py', 'r').read()
        pipeline_script = open('cendr/task/pipeline.R', 'r').read()
        models = open('cendr/models.py', 'r').read()
        params += [{'key':'startup-script','value': startup_script}]
        params += [{'key':'run_pipeline','value': run_pipeline}]
        params += [{'key':'pipeline','value':pipeline_script}]
        params += [{'key':'models','value':models}]

        # Ensure there are not too many instances running
        while instance_count() > 5:
            time.sleep(20)

        create_mapping_instance(gce_name, params)
        return "", 200
    except:
        return "", 400


