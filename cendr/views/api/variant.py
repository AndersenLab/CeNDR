# NEW API
from cendr import app, build
from cyvcf2 import VCF
from flask import jsonify, request
import re
import sys
from cendr.models import wb_gene
from cendr.views.api.gene import gene_search
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE

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


@app.route('/api/variant', methods=["GET", "POST"])
def variant_api():
    query = request.args
    query = {'chrom': query['chrom'],
             'start': int(query['start']),
             'end': int(query['end']),
             'variant_impact': query['variant_impact'].split("_"),
             'sample_tracks': query['sample_tracks'].split("_")}
    app.logger.info(query)
    version = request.args.get('version') or  build
    samples = query['sample_tracks']
    if not samples[0]:
        samples = "N2"
    else:
        samples = ','.join(samples)
    vcf = "http://storage.googleapis.com/elegansvariation.org/releases/{version}/WI.{version}.vcf.gz".format(
        version=version)

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
        json_out = []

        v = VCF(f.name)

        if samples:
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

            print(record)
            gt_set = zip(v.samples, record.gt_types.tolist(), record.format("FT").tolist(), record.gt_bases.tolist())
            gt_set = [dict(zip(gt_set_keys, x)) for x in gt_set if x[1] != 2] # Filter missing (2)
            ANN = [x for x in ANN if x['impact'] in query['variant_impact']]
            rec_out = {
                "CHROM": record.CHROM,
                "POS": record.POS,
                "REF": record.REF,
                "ALT": record.ALT,
                "GT": gt_set,
                "AF": INFO["AF"],
                "ANN": ANN
            }
            if 'phastcons' in INFO:
                rec_out["phastcons"] = float(INFO['phastcons'])
            if 'phylop' in INFO:
                rec_out["phylop"] = float(INFO['phylop'])
            if len(rec_out['ANN']) > 0 or 'ALL' in query['variant_impact']:
                json_out.append(rec_out)
            if i == 1000:
                return jsonify(json_out)
        return jsonify(json_out)
