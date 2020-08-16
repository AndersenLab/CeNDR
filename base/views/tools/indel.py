
import fileinput, glob
import json, re

dFileDa = {}
tmp = {}
for l in fileinput.input("./data/filter_combined2.bed"):
	if not l.startswith("CHROM") and not l.startswith('\n'):
		da = l.split('\t')
		if not da[0] in dFileDa: dFileDa[da[0]] = []
        # Sets region
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

def checkOverlap(t, q):
    q = [float(i) for i in q]
    for i in t:
        if min(q) <= float(i) <= max(q):
            return False
    if all(i < min(q) for i in t):
        return False
    return True
