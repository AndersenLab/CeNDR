#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Script for generating an interval summary

"""
import pandas as pd
from subprocess import Popen
from utils.vcf_np import VCF_DataFrame

def process_interval(interval):
    """
        Processes an interval - producing a JSON summary in the data folder.
    """
    # Download the VCF
    interval_fname = interval.replace(":", "-")
    interval_out = interval_fname + ".vcf.gz"

    # Subset VCF by isotypes
    df = pd.read_csv("df.tsv", sep='\t')
    isotype_list = ','.join(df['ISOTYPE'].values)
    comm = f"bcftools view -O z --samples {isotype_list} http://storage.googleapis.com/elegansvariation.org/releases/20170531/WI.20170531.vcf.gz {interval} > {interval_out}"
    out, err = Popen(comm, shell=True).communicate()
    vcf = VCF_DataFrame.from_vcf(interval_out)
    return vcf.hard_filter() \
              ._prune_alleles() \
              ._prune_non_snps() \
              .interval_summary()
