
# backup first

with open("../ancillary/gs_file_locs.tsv", 'r') as f:
    for line in f.readlines():
        line = line.strip()
        if line.endswith("LDplot-1.png"):
            to = line.replace("LDplot-1.png","LD.png")
            print "gsutil cp %s %s" % (line, to)
        if line.endswith("PxGplot-1.png"):
            to = line.replace("PxGplot-1.png","PxG.png")
            print "gsutil cp %s %s" % (line, to)
        elif line.endswith("Manplot-1.png"):
            to = line.replace("Manplot-1.png","Manhattan.png")
            print "gsutil cp %s %s" % (line, to)
        elif line.endswith("processed_sig_mapping.tsv"):
            to = line.replace("processed_sig_mapping.tsv","mapping.tsv")
            print "gsutil cp %s %s" % (line, to)
        elif line.endswith("non_sig_mapping.tsv"):
            to = line.replace("non_sig_mapping.tsv","mapping.tsv")
            print "gsutil cp %s %s" % (line, to)
        elif line.endswith("phenotype_histogram-1.png"):
            to = line.replace("phenotype_histogram-1.png","Phenotype.png")
            print "gsutil cp %s %s" % (line, to)
        elif line.endswith("unnamed-chunk-6-1.png"):
            print "gsutil rm %s" % (line)
        elif line.endswith("unnamed-chunk-7-1.png"):
            print "gsutil rm %s" % (line)
        elif line.endswith("QQplot-1.png"):
            print "gsutil rm %s" % (line)
        elif line.endswith("raw_mapping.tsv"):
            to = line.replace("raw_mapping.tsv","raw.mapping.tsv")
            print """gsutil cat %s | awk 'NR == 1 { print } $5 != 0 { print }' | gsutil cp - %s""" % (line, to)


#
# LATER, GO BACK AND REMOVE -1.png files.
#