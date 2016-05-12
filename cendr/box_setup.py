# coding: utf-8

from __future__ import print_function, unicode_literals

import bottle
import os
from threading import Thread, Event
import webbrowser
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server
import json
import yaml
from collections import defaultdict

from boxsdk import OAuth2, Client

box_cred = json.loads(open("box.json").read())
CLIENT_ID = box_cred["CLIENT_ID"] # Insert Box client ID here
CLIENT_SECRET = box_cred["CLIENT_SECRET"]   # Insert Box client secret here


def authenticate():
    class StoppableWSGIServer(bottle.ServerAdapter):
        def __init__(self, *args, **kwargs):
            super(StoppableWSGIServer, self).__init__(*args, **kwargs)
            self._server = None

        def run(self, app):
            server_cls = self.options.get('server_class', WSGIServer)
            handler_cls = self.options.get('handler_class', WSGIRequestHandler)
            self._server = make_server(self.host, self.port, app, server_cls, handler_cls)
            self._server.serve_forever()

        def stop(self):
            self._server.shutdown()

    auth_code = {}
    auth_code_is_available = Event()

    local_oauth_redirect = bottle.Bottle()

    @local_oauth_redirect.get('/')
    def get_token():
        auth_code['auth_code'] = bottle.request.query.code
        auth_code['state'] = bottle.request.query.state
        auth_code_is_available.set()

    port = 8002
    local_server = StoppableWSGIServer(host='localhost', port=port)
    server_thread = Thread(target=lambda: local_oauth_redirect.run(server=local_server))
    server_thread.start()

    oauth = OAuth2(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
    auth_url, csrf_token = oauth.get_authorization_url('http://localhost:' + str(port))
    webbrowser.open(auth_url)

    auth_code_is_available.wait()
    local_server.stop()
    assert auth_code['state'] == csrf_token
    access_token, refresh_token = oauth.authenticate(auth_code['auth_code'])

    print('access_token: ' + access_token)
    print('refresh_token: ' + refresh_token)

    return oauth


if __name__ == '__main__':
    client = Client(authenticate())
    bam = client.folder(folder_id="6547362613").get_items(limit = 100000)
    cram = client.folder(folder_id="6560143373").get_items(limit = 100000)
    [x.create_shared_link(access = "open") for x in bam + cram]
    files = {x["name"]:x.get_shared_link_download_url() for x in bam + cram if x.get().size > 0}
    dict_out = {}
    for f, link in files.items():
        isotype = f.split(".")[0]
        if isotype not in dict_out.keys():
            dict_out[isotype] = {}
            dict_out[isotype]["bam"] = ""
            dict_out[isotype]["bam.bai"] = ""
            dict_out[isotype]["cram"] = ""
            dict_out[isotype]["cram.crai"] = ""
            dict_out[isotype]["tsv"] = ""
        dict_out[isotype][".".join(f.split(".")[1:])] = link
    with open("static/content/data/urls.tsv", 'w') as f:
        for i in dict_out:
            f.write('\t'.join([i, dict_out[i]["bam"], dict_out[i]["bam.bai"], dict_out[i]["cram"], dict_out[i]["cram.crai"], dict_out[i]["tsv"]]) + "\n")
    os._exit(0)