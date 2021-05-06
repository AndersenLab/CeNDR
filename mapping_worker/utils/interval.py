#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Script for generating an interval summary

"""
import pandas as pd
import os
from subprocess import Popen
from utils.vcf_np import VCF_DataFrame
from logzero import logger
from base.constants import GOOGLE_CLOUD_BUCKET

DATASET_RELEASE = os.environ['DATASET_RELEASE']


def process_interval(interval):
    """
        Processes an interval - producing a JSON summary in the data folder.
    """
    logger.info(f"Generating interval summary for {interval}")
    # Download the VCF
    interval_fname = interval.replace(":", "-")
    interval_out = interval_fname + ".vcf.gz"
    variants_out = interval_fname + ".variants.tsv.gz"

    # Subset VCF by isotypes
    df = pd.read_csv("df.tsv", sep='\t')
    isotype_list = ','.join(df['ISOTYPE'].values)
    if not os.path.exists(interval_out):
        comm = f"bcftools view -O z --samples {isotype_list} https://storage.googleapis.com/{GOOGLE_CLOUD_BUCKET}/releases/{DATASET_RELEASE}/variation/WI.{DATASET_RELEASE}.soft-filter.vcf.gz {interval} > {interval_out} && bcftools index {interval_out}"
        out, err = Popen(comm, shell=True).communicate()
    vcf = VCF_DataFrame.from_vcf(interval_out, interval)

    # Join interval variants here
    interval_variants = pd.read_csv("data/interval_variants.tsv.gz", sep="\t")

    # Prune VCF
    vcf = vcf.hard_filter() \
              ._prune_alleles() \
              ._prune_non_snps()

    # Full join
    print("Outputting Variants")
    vcf[['CHROM', 'POS', 'REF', 'ALT', 'allele_set',  'aaf', 'call_rate', 'is_snp', 'is_indel', 'is_transition', 'nucl_diversity', 'num_called', 'num_het', 'num_hom_alt', 'num_hom_ref', 'ANN']].to_csv("data/" + variants_out, sep="\t", compression='gzip', index=False)
    return vcf.interval_summary_table()
