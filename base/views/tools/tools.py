import os
import gzip
from flask import render_template, Blueprint, redirect, url_for
from base.views.api.api_strain import get_strains
from base.constants import CHROM_NUMERIC
from logzero import logger

from wtforms import (Form,
                     StringField,
                     TextAreaField,
                     IntegerField,
                     SelectField,
                     FieldList,
                     HiddenField,
                     RadioField)
from wtforms.validators import Required, Length, Email, DataRequired
from wtforms.validators import ValidationError

#
# Gene View
#
tools_bp = Blueprint('tools',
                     __name__,
                     template_folder='tools')

@tools_bp.route('/')
def tools():
    VARS = {"title": "Tools"}
    return render_template('tools/tools.html', **VARS)

@tools_bp.route('/heritability')
def heritability_calculator():
    VARS = {"title": "Heritability Calculator"}
    return render_template('tools/heritability_calculator.html', **VARS)


#===========================#
#   pairwise_indel_finder   #
#===========================#

print(os.getcwd())
# Initial load of data
# This is run when the server is started.
strains = []
with gzip.open("base/static/data/pairwise_indel_finder/sv_data.bed.gz", 'rb') as f:
    for line in f.readlines():
        line = line.decode("UTF-8").split("\t")
        strains.append(line[8])

logger.debug("Done loading strains")

strains = sorted(list(set(strains)))


class pairwise_indel_form(Form):
    """
        Form for mapping submission
    """
    strain_1 = SelectField('strain_1', choices=strains, [Required()])
    strain_2 = SelectField('strain_2', choices=strains, [Required()])



@tools_bp.route('/tools/pairwise_indel_finder', methods=['GET'])
def pairwise_indel_finder():
    VARS = {"title": "Pairwise Indel Finder",
            "strains": strains,
            "chroms": CHROM_NUMERIC.keys()}
    return render_template('tools/pairwise_indel_finder.html', **VARS)

@tools_bp.route("/tools/pairwise_indel_finder/getData1", methods=["POST"])
def get_indel():
    clicked=None
    res = []
    chkDict = {}
    chkDictF = {}
    if request.method == "POST" or request.method == "GET":
        clicked=request.get_json()
        strns = [clicked['id1'], clicked['id2']]
        if clicked['chrom'] in dFileDa:
            for da in dFileDa[clicked['chrom']]:
                if (int(da["start"])>= int(clicked['start']) and int(da["start"])< int(clicked['stop'])):
                    k = da["svpos"]
                    t = [da["start"], da["end"], da["size"], [da["strain"][i]+"("+da["svtype"][i]+")" for i in range(len(da["strain"])) if da["strain"][i] in strns]]
                    if len(t[3]) > 0: 
                        if not k in chkDict: chkDict[k]= []
                        chkDict[k].append(t)

        inc = 1
        for k in chkDict:
            dal = [k.split(':')[0], ] + chkDict[k][0]
            tm = [chkDict[k][0][-1]]
            
            dal[-1] = ' - '.join(list(set([t[0] for t in tm])))
            inc +=1
            res.append(dal)
        return (json.dumps({"data": res}))