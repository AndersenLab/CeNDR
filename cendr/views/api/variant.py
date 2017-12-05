# NEW API
from cendr import app, get_vcf
from cyvcf2 import VCF
from flask import jsonify, request, Response
import re
from cendr.views.api.gene import gene_search
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE
from collections import OrderedDict

ANN_header = ["allele",
              "effect",
              "impact",
              "gene_name",
              "gene_id",
              "feature_type",
              "feature_id",
              "transcript_biotype",
              "exon_intron_rank",
              "nt_change",
              "aa_change",
              "cDNA_position/cDNA_len",
              "protein_position",
              "distance_to_feature",
              "error"]


def get_region(region):
    region = region.replace(",", "")
    m = re.match("^([0-9A-Za-z]+):([0-9]+)-([0-9]+)$", region)
    if m:
        chrom = m.group(1)
        start = int(m.group(2))
        end = int(m.group(3))
        gene = None
    else:
        # Resolve gene/location
        gene = gene_search(region)
        if not gene:
            return "Invalid region", 400
        chrom = gene["CHROM"]
        start = gene["start"]
        end = gene["end"]
    region = "{chrom}:{start}-{end}".format(**locals())
    return region, chrom, start, end, gene


gt_set_keys = ["SAMPLE", "GT", "FT", "TGT"]


ann_cols = ['allele',
            'effect',
            'impact',
            'gene_name',
            'gene_id',
            'feature_type',
            'feature_id',
            'transcript_biotype',
            'exon_intron_rank',
            'nt_change',
            'aa_change',
            'protein_position',
            'distance_to_feature']


@app.route('/api/variant', methods=["GET", "POST"])
def variant_api():
    query = request.args
    query = {'chrom': query['chrom'],
             'start': int(query['start']),
             'end': int(query['end']),
             'variant_impact': query['variant_impact'].split("_"),
             'sample_tracks': query['sample_tracks'].split("_"),
             'output': query['output'],
             'list-all-strains': query['list-all-strains']
            }
    app.logger.info(query)
    samples = query['sample_tracks']
    if query['list-all-strains'] == 'true':
        samples = "ALL"
    elif not samples[0]:
        samples = "N2"
    else:
        samples = ','.join(samples)
    vcf = get_vcf()

    chrom = query['chrom']
    start = query['start']
    end = query['end']

    if start >= end:
        return "Invalid start and end region values", 400
    #if end - start > 1e5:
    #    return jsonify('error': "You can only query a maximum of 100 kb"), 400

    region = "{chrom}:{start}-{end}".format(**locals())
    comm = ["bcftools", "view", vcf, region]
    # Query Severity

    # Query samples
    if samples != 'ALL':
        comm = comm[0:2] + ['--force-samples', '--samples', samples] + comm[2:]
    app.logger.info(' '.join(comm))
    out, err = Popen(comm, stdout=PIPE, stderr=PIPE).communicate()
    if not out and err:
        app.logger.error(err)
        return err, 400
    tfile = NamedTemporaryFile(mode='w+b', bufsize=10000)
    with tfile as f:
        f.write(out)
        f.flush()
        output_data = []

        v = VCF(f.name)

        if samples and samples != "ALL":
            samples = samples.split(",")
            incorrect_samples = [x for x in samples if x not in v.samples]
            if incorrect_samples:
                return "Incorrectly specified sample(s): " + ','.join(incorrect_samples), 400

        for i, record in enumerate(v):
            INFO = dict(record.INFO)

            ANN = []
            if "ANN" in INFO.keys():
                ANN_set = INFO['ANN'].split(",")
                if len(ANN_set) == 0 and not output_all_variants:
                    break
                for ANN_rec in ANN_set:
                    ANN.append(dict(zip(ANN_header, ANN_rec.split("|"))))
                del INFO['ANN']

            gt_set = zip(v.samples, record.gt_types.tolist(), record.format("FT").tolist(), record.gt_bases.tolist())
            gt_set = [dict(zip(gt_set_keys, x)) for x in gt_set]
            ANN = [x for x in ANN if x['impact'] in query['variant_impact']]
            rec_out = {
                "CHROM": record.CHROM,
                "POS": record.POS,
                "REF": record.REF,
                "ALT": record.ALT,
                "FILTER": record.FILTER or 'PASS', # record.FILTER is 'None' for PASS
                "GT": gt_set,
                "AF": INFO["AF"],
                "ANN": ANN
            }
            if 'phastcons' in INFO:
                rec_out["phastcons"] = float(INFO['phastcons'])
            if 'phylop' in INFO:
                rec_out["phylop"] = float(INFO['phylop'])
            if len(rec_out['ANN']) > 0 or 'ALL' in query['variant_impact']:
                output_data.append(rec_out)
            if i == 1000 and query['output'] != "tsv":
                return jsonify(output_data)
        if query['output'] == 'tsv':
            filename = '_'.join([query['chrom'], str(query['start']), str(query['end'])])
            build_output = OrderedDict()
            output = []
            header = False
            for rec in output_data:
                for k in ['CHROM', 'POS', "REF", "ALT", "FILTER", "phastcons", "phylop", "AF"]:
                    if k == 'ALT':
                        build_output[k]  = ','.join(rec[k])
                    else:
                        build_output[k]  = rec.get(k) or "NA"
                if rec['ANN']:
                    for ann in rec['ANN']:
                        for k in ann_cols:
                            build_output[k] = ann.get(k) or "NA"
                else:
                    for k in ann_cols:
                        build_output[k] = ""

                for gt in rec['GT']:
                    sample = gt['SAMPLE']
                    build_output[sample + '_GT'] = gt['GT']
                    build_output[sample + '_FT'] = gt['FT']
                if header is False:
                    output.append('\t'.join(build_output.keys()))
                    header = True

                output.append('\t'.join(map(str,build_output.values())))
            return Response('\n'.join(output), mimetype="text/csv", headers={"Content-disposition":"attachment; filename=%s" % filename})
        return jsonify(output_data)


