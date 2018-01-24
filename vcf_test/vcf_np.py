import os
import pandas as pd
from cyvcf2 import VCF
import numpy as np

v = VCF("WI.20170531.snpeff.vcf.gz")



data = []
attrs = ['CHROM',
         'POS',
         'REF',
         'ALT',
         'FILTER',
         'aaf',
         'nucl_diversity',
         'is_snp',
         'is_indel',
         'call_rate',
         'num_called',
         'num_het',
         'num_hom_ref',
         'num_hom_alt',
         'ploidy',
         'start',
         'end',
         'is_transition']

for line in v("I:1-1000000"):
    var_line = {attr:getattr(line, attr) for attr in attrs if hasattr(line, attr)}
    var_line['samples'] = v.samples
    var_line['FT'] = list(line.format("FT"))
    ANN = line.INFO.get("ANN")
    if ANN:
        var_line['ANN'] = [x.split("|") for x in ANN.split(",")]
    var_line['DP'] = list([int(x) for x in np.ndarray.flatten(line.format("DP"))])
    #var_line.update({f"INFO_{k}": v for k, v in dict(line.INFO).items()})
    data.append(var_line)

df = pd.DataFrame(data)

df.to_parquet('df.parquet', engine='pyarrow')

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

class ANN:
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

def fetch_annotation_column(annotations, column):
    if annotations is not np.nan:
        ann_column_index = ANN_header.index(column)
        return [x[ann_column_index] for x in annotations]
    return np.nan


class pd_vcf:

    def __init__(self, df):
        self.df = df

    def n_variants(self, chrom, start, end):
        query_string = f"CHROM == '{chrom}' & POS > {start} & POS < {end}"
        return self.df.query(query_string).CHROM.count()


    class ANNO:
        
        def fetch_annotation_column(annotations, )

        def __init__(self):
            for ann in ANN_header:
                setattr(self, ann, property(lambda x: fetch_annotation_column(x, ann) if type(x) == list else x))



    ANN = ANNO()


pdv = pd_vcf(df)


pdv.n_variants(chrom="I", start=0, end=10000)


