import httplib2
import base64
import json
from apiclient import discovery
from oauth2client import client as oauth2client

PUBSUB_SCOPES = ['https://www.googleapis.com/auth/pubsub']

def create_pubsub_client(http=None):
    credentials = oauth2client.GoogleCredentials.get_application_default()
    if credentials.create_scoped_required():
        credentials = credentials.create_scoped(PUBSUB_SCOPES)
    if not http:
        http = httplib2.Http()
    credentials.authorize(http)

    return discovery.build('pubsub', 'v1', http=http)

client = create_pubsub_client()

def queue_message(message, queue_name = "cegwas-map"):
    queue_name = 'projects/andersen-lab/topics/' + queue_name
    message = base64.b64encode(json.dumps(message))
    body = {
        "messages":
            {"data": message}
    }
    resp = client.projects().topics().publish(
        topic=queue_name, body=body).execute()
    return resp