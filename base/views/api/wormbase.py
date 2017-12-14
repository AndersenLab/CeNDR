from base.models import strain, wb_gene
from base.application import app, cache, ds
from flask import Response, jsonify
import requests
from xml.dom import minidom

@app.route('/api/wormbase/<path:r>')
@cache.memoize(50)
def wormbase_api(r):
    r = requests.get('http://www.wormbase.org/rest/' + r, headers = {'Content-Type': 'application/json; charset=utf-8'}
)
    return Response(r.text, mimetype="text/json")



@app.route('/api/omim/<string:gene_name>')
@cache.memoize(50)
def omim(gene_name):
    gene_id = wb_gene.get(Name = gene_name)
    r = requests.get('http://www.wormbase.org/rest/widget/gene/%s/human_diseases' % gene_id.Name,
                    headers = {'Content-Type': 'application/json; charset=utf-8'}).json()
    r = r["fields"]["human_diseases"]["data"]
    omim_models, omim_genes, omim_diseases, response = {}, [], [], {}
    if r:
        if "potential_model" in r:
            omim_models = {x["id"]:x["label"] for x in r["potential_model"]}
        if "gene" in r:
            omim_genes = r["gene"]
        if "disease" in r:
            omim_diseases = r["disease"]
        api_key = ds.get(ds.key("credential", "OMIM"))["apiKey"]
        omim_url = "http://api.omim.org/api/entry?mimNumber={omim_ids}&apiKey={api_key}"
        omim_url = omim_url.format(omim_ids = ','.join(omim_genes + omim_diseases), api_key = api_key)
        omim_results = requests.get(omim_url).text
        dom = minidom.parseString(omim_results)
        omim_results = {x[1].firstChild.nodeValue:
         x[0].firstChild.nodeValue for x in zip(dom.getElementsByTagName("preferredTitle"),
         dom.getElementsByTagName("mimNumber"))}
        response = {"omim_diseases": {x: omim_results[x] for x in omim_diseases},
                    "omim_genes" : {x: omim_results[x] for x in omim_genes}}
    return jsonify(response)
