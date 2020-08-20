
import fileinput, glob
import json, re
import utils.primer

dFileDa = {}
tmp = {}
for l in fileinput.input("./data/filter_combined2.bed"):
	if not l.startswith("CHROM") and not l.startswith('\n'):
		da = l.split('\t')
		if not da[0] in dFileDa: dFileDa[da[0]] = []
		reg = da[0]+":"+"-".join([da[1], da[2]])
		if int(da[-3]) >= 50 and int(da[-3]) <= 500:
			if reg not in tmp :
				tmp[reg] = {"start":da[1], "end":da[2], "strain":[da[8],], "svpos":reg, "svtype":[[da[4],],], "size":da[-3]}
			else:
				if not da[8] in tmp[reg]["strain"]:
					tmp[reg]["strain"].append(da[8])
					tmp[reg]["svtype"].append([da[4],])
				else:
					tmp[reg]["svtype"][tmp[reg]["strain"].index(da[8])] = list(set(tmp[reg]["svtype"][tmp[reg]["strain"].index(da[8])] + [da[4],])) 

for r in tmp:
	tmp[r]["svtype"] = [','.join(i) for i in tmp[r]["svtype"]]
	dFileDa[r.split(':')[0]].append(tmp[r])

strains = [l.strip() for l in fileinput.input("./data/strains.txt")]

chroms = ['I', 'II', 'III', 'IV', 'V', 'X'] 

def checkOverlap( t, q):
	q = [float(i) for i in q]
	for i in t:
		if min(q) <= float(i) <= max(q):
			return False
	if all( i < min(q) for i in t):
		return False
	return True


@app.route('/tools/pairwise_indel_finder', methods=['GET'])
def landing():
	return render_template('tools/pairwise_indel_finder.html', strains=strains, chroms=chroms)

@app.route('/tools/pairwise_indel_finder/primers', methods=['GET'])
def getPrimers():
	results = []
	data = request.args.get('input').split(',')
	primer_arg = ['primer', 'indel', '--ref=./data/genome/c_elegans.PRJEB28388.WS273.fa.gz', '--region='+data[0]+':'+data[1]+'-'+data[2], '--samples='+data[-1].split('(')[0], './data/WI.HARD_FILTERED.FP.vcf.gz' ]
	results = primer.main(primer_arg)
	if isinstance(results, str):
		render_template('/tools/noVCF.html', err= results)
	da = []
	strains = data[-2:]
	search_reg = data[-3]
	indel_reg = data[0]+':'+data[1]+'-'+data[2]
	primer_reg = [1000000000, 0, 1000000000, 0]
	amp_reg = [1000000000, 0,""]
	for r in results:
		tmp = []
		if len(r) >= 17:
			if not r[0] == "CHROM":
				t=r[15].split(",")
				if (checkOverlap([r[10], r[11], r[13], r[14]], [data[1], data[2]]) and not checkOverlap( t, [55, 65])) and ((float(r[10]) < float(data[1])) and (float(r[14]) > float(data[2]))) :
					tmp.append(r[9])
					tmp.append(r[10])
					tmp.append(r[11])
					tmp.append(t[0])
					tmp.append(r[12])
					tmp.append(r[13])
					tmp.append(r[14])
					tmp.append(t[1])
					tmp.append(r[16])
					tmp.append(r[17])

					if r[10] < primer_reg[0]: 
						primer_reg[0] = r[10]
						primer_reg[1] = r[11]
					if r[14] > primer_reg[3]: 
						primer_reg[3] = r[14]
						primer_reg[2] = r[13]
					elif r[13] > primer_reg[3]:
						primer_reg[2] = r[14]
						primer_reg[3] = r[13]
					ttm = r[18].split(':')[1].split('-')
					if int(ttm[1]) > amp_reg[1]: amp_reg[1] = int(ttm[1])
					if int(ttm[0]) < amp_reg[0]: amp_reg[0] = int(ttm[0])
					amp_reg[2] = r[0]
		if not tmp == []: da.append(tmp)
	ampreg = amp_reg[2]+':'+str(amp_reg[0])+'-'+str(amp_reg[1]) 
	gd = {"search_reg": ampreg, "primer_reg": primer_reg, "indel_reg":indel_reg}
	if ampreg.startswith(":"): ampreg = '-'
	par = ["Strain 1 : "+strains[0], "Strain 2 : "+strains[1], "Search reg : "+search_reg, "Amplicon size range : 200-1500", "Primer length : 16-26 bp", "Annealing temp : 55-65ºC"]
	return render_template('tools/primers.html', data1=data, chroms=chroms, pres=da, graphd=gd, params=par, fnam="primers_"+re.sub("[:-]", "_", indel_reg))

@app.route('/tools/pairwise_indel_finder/getData1', methods=['POST', 'GET'])
def getIndel():
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