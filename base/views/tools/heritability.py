
import fileinput, glob
import json, re
import time, os
from datetime import datetime

#####################################################
## Absolute path to the jobsD folder within the site structure.
## Edit this according to site folder structure, for docker execution for H2script.
jobsDpath = "/"

#####################################################
@app.route('tools/heritability_calculator_res', methods=['GET', 'POST'])
def getRes():
	if request.method == "POST" or request.method == "GET":
		results = []
		ctd = []
		data = request.args.get('jbd')
		##print(os.path.isfile('./jobsD/'+data+'.txt'))
		if os.path.isfile('./jobsD/'+data+'.out'): 
			for li in fileinput.input('./jobsD/'+data+'.txt'):
				if not li.startswith("AssayNumber"): results.append(li.rstrip().split(','))
				
			with open('./jobsD/'+data+'.json') as json_file:
				ctd = json.load(json_file)
			
			trait = ctd[1]['t']
			
			da = []
			for li in fileinput.input('./jobsD/'+data+'.out'):
				if not li.startswith('"H2"'): da = [str("{:.2f}".format(float(x)*100)) for x in li.rstrip().split('\t')[1:]]
			XX = da[0]
			X = da[1]
			Y = da[2]
			return(render_template('tools/heritability_calculator_res.html', res=results, cdt=json.dumps(ctd), trait=trait, XX=XX, X=X, Y=Y, fnam=datetime.today().strftime('%Y%m%d.')+trait))
	return render_template('tools/heritability_calculator_processing.html')


@app.route('/checkHTdata', methods=['GET', 'POST'])
def checkHTData():
	from numpy import percentile 
	import statistics as st
	data = []
	res = {}
	if request.method == "POST" or request.method == "GET":
		clicked=request.get_json()
		htcalData = json.loads(clicked)
		print(htcalData)
		for i in range(len(htcalData)):
			if htcalData[i][4] is not None and not (htcalData[i][4] == ""):
				if not (htcalData[i][4] == "NA"  or "Strain" in htcalData[i]):
					data.append(float(htcalData[i][4]))
		
		res = {}
		res["variance"] = "{:.2f}".format(st.variance(data))
		res["sd"] = "{:.2f}".format(st.stdev(data))
		res["minimum"] = "{:.2f}".format(min(data))
		res["maximum"] = "{:.2f}".format(max(data)) 
		All_quartiles = percentile(data, [25, 50, 75])
		res["25% quartile"] = "{:.2f}".format(All_quartiles[0])
		res["50% quartile"] = "{:.2f}".format(All_quartiles[1])
		res["75% quartile"] = "{:.2f}".format(All_quartiles[2])
		
	return res	

@app.route('/getHTdata', methods=['GET', 'POST'])
def getHTData():
	global jbid
	if request.method == "POST" or request.method == "GET":
		clicked=request.get_json()
		htcalData = json.loads(clicked)
		## create chartData.
		flag = 0
		if (clicked == ""): flag = 1
		clicked = ""
		chData = []
		jbd = "htj_"+str(jbid)+"_"+str(time.time())
		jbid+=1
		#create url
		u = "/indexHT_res?jbd="+jbd
		trait = []
		with open("./jobsD/"+jbd+'.txt', 'w') as out:
			out.write(','.join(['AssayNumber', 'Strain', 'TraitName', 'Replicate', 'Value'])+'\n')
			for i in range(len(htcalData)):
				if htcalData[i][4] is not None and not (htcalData[i][4] == ""):
					if not (htcalData[i][4] == "NA"  or "Strain" in htcalData[i]):
						out.write(','.join(htcalData[i])+'\n')
						if not htcalData[i][2] in trait: trait.append(htcalData[i][2])
						chData.append({"a":htcalData[i][0],"s":htcalData[i][1],"v":htcalData[i][4],"t":htcalData[i][2]}) #+"_"+htcalData[i][1]+"_"+htcalData[i][3]})

		with open("./jobsD/"+jbd+'.json', 'w') as out:
			out.write(json.dumps(chData))
			
		#start execution
		if len(trait) > 1 : u = ""
		else:
			import os
			pid = os.spawnvp(os.P_NOWAIT, 'docker', ['docker', 'run', '-v', jobsDpath+'/jobsD:/home/data', 'nwuniv/htcal.v1.0', 'Rscript', '/home/script/H2_script.R', '/home/data/'+jbd+'.txt', '/home/data/'+jbd+'.out'])
		#return url
		#if pid == "": u = ""
		return(json.dumps({"url": u}))
