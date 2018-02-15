#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Script/Tools for working with a VCF in python.

Used for generating the interval summary.

"""
import json
import re
import pandas as pd
import numpy as np
import itertools
from collections import defaultdict, Counter
from cyvcf2 import VCF
from pandas import DataFrame, Series
from logzero import logger
from functools import reduce

def infinite_dict():
    return defaultdict(infinite_dict)


def flatten_cols(df):
    """
        Flattens hierarchical columns

        Stack Overflow: 14507794
    """
    df.columns = [
        '_'.join(tuple(map(str, t))).rstrip('_') 
        for t in df.columns.values
        ]
    return df



ANN_FIELDS = ["allele",
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
              "cdna_pos",
              "protein_position",
              "distance_to_feature",
              "error"]


def grouper(n, iterable):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


class AnnotationItem(Series):

    @property
    def _constructor(self):
        return AnnotationItem

    @property
    def _constructor_expanddim(self):
        return VCF_DataFrame

    def __eq__(self, other):
        return AnnotationItem(self.apply(lambda row: other in row if type(row) == list else False))

    @property
    def length(self):
        result = self.apply(lambda row: len(row) if type(row) == list else 0)
        return AnnotationItem(data=result)


class AnnotationSeries(Series):
    # https://stackoverflow.com/q/48435082/2615190
    our_column_names = ('ANN',)

    def __new__(cls, *args, **kwargs):
        if kwargs.get('name', '') in cls.our_column_names:
            obj = object.__new__(cls)
            obj.__init__(*args, **kwargs)
            return obj
        return pd.Series(*args, **kwargs)


    def __eq__(self, other):
        return self.apply(lambda row: other in row if type(row) == list else False)

    @property
    def _constructor(self):
        return AnnotationSeries

    @property
    def _constructor_expanddim(self):
        return VCF_DataFrame

    def _fetch_field(self, field):
        """
            Highly redundant - but I could
            figure out a way to dynamically specify properties.
        """
        ann_column_index = ANN_FIELDS.index(field)
        result = self.apply(lambda row: [x[ann_column_index] for x in row] if type(row) == list else np.nan)
        return AnnotationSeries(data=result, name='ANN')

    @property
    def allele(self):
        result = self._fetch_field('allele')
        return AnnotationItem(data=result, name='ANN')

    @property
    def effect(self):
        result = self._fetch_field('effect')
        return AnnotationItem(data=result, name='ANN')

    @property
    def impact(self):
        result = self._fetch_field('impact')
        return AnnotationItem(data=result, name='ANN')

    @property
    def gene_name(self):
        result = self._fetch_field('gene_name')
        return AnnotationItem(data=result, name='ANN')

    @property
    def gene_id(self):
        result = self._fetch_field('gene_id')
        return AnnotationItem(data=result, name='ANN')

    @property
    def feature_type(self):
        result = self._fetch_field('feature_type')
        return AnnotationItem(data=result, name='ANN')

    @property
    def feature_id(self):
        result = self._fetch_field('feature_id')
        return AnnotationItem(data=result, name='ANN')

    @property
    def transcript_biotype(self):
        result = self._fetch_field('transcript_biotype')
        return AnnotationItem(data=result, name='ANN')

    @property
    def exon_intron_rank(self):
        result = self._fetch_field('exon_intron_rank')
        return AnnotationItem(data=result, name='ANN')

    @property
    def nt_change(self):
        result = self._fetch_field('nt_change')
        return AnnotationItem(data=result, name='ANN')

    @property
    def aa_change(self):
        result = self._fetch_field('aa_change')
        return AnnotationItem(data=result, name='ANN')

    @property
    def cnda_pos(self):
        result = self._fetch_field('cnda_pos')
        return AnnotationItem(data=result, name='ANN')

    @property
    def protein_pos(self):
        result = self._fetch_field('protein_pos')
        return AnnotationItem(data=result, name='ANN')

    @property
    def distance_to_feature(self):
        result = self._fetch_field('distance_to_feature')
        return AnnotationItem(data=result, name='ANN')

    @property
    def error(self):
        result = self._fetch_field('error')
        return AnnotationItem(data=result, name='ANN')


class VCF_DataFrame(DataFrame):

    _metadata = ['samples', 'interval', 'chrom', 'start', 'end']

    attrs = ['CHROM',
             'POS',
             'ID',
             'REF',
             'ALT',
             'QUAL',
             'FILTER',
             'start',
             'end',
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
             'is_transition']

    def __init__(self, *args, **kwargs):
        super(VCF_DataFrame, self).__init__(*args, **kwargs)

    @property
    def _constructor(self):
        return VCF_DataFrame

    @property
    def _constructor_sliced(self):
        return AnnotationSeries

    @classmethod
    def from_vcf(cls, filename, interval=None):
        """
            Create a numpy-array VCF object.

            filename:
                Name of the VCF
            interval:
                An interval of the VCF to use (chrom:start-end)
        """
        vcf = VCF(filename, gts012=True)
        rows = []
        for i, line in enumerate(vcf(interval)):
            var_line = {}
            var_line = {attr: getattr(line, attr) for attr in cls.attrs if hasattr(line, attr)}
            # Currently string lists must be encoded using python.
            var_line['FT'] = line.format("FT")
            var_line['TGT'] = line.gt_bases

            var_line['DP'] = line.format("DP").flatten().astype(np.int64)
            var_line['GT'] = line.gt_types.astype(np.int64)
            ANN = line.INFO.get("ANN")
            if ANN:
                var_line['ANN'] = [x.split("|") for x in ANN.split(",")]
            rows.append(var_line)
        dataset = DataFrame.from_dict(rows)

        # Convert to categorical
        dataset.REF = pd.Categorical(dataset.REF)
        dataset.FILTER = pd.Categorical(dataset.FILTER)

        # Add num missing column
        dataset['num_missing'] = dataset.GT.apply(lambda row: np.sum(np.isin(row, ['./.', '.|.'])))

        # Use ordered CHROM
        dataset.CHROM = pd.Categorical(dataset.CHROM,
                                       ordered=True,
                                       categories=vcf.seqnames)

        dataset.REF = pd.Categorical(dataset.REF)
        dataset.FILTER = pd.Categorical(dataset.FILTER)

        # Add samples
        dataset = VCF_DataFrame(dataset)
        dataset.samples = np.array(vcf.samples)
        if interval:
            dataset.interval = interval
            chrom, start, end = re.split(":|\-", interval)
            dataset.chrom = chrom
            dataset.start = int(start)
            dataset.end = int(end)
        dataset['allele_set'] = dataset.TGT.apply(lambda x: set([a for a in sum([re.split("\||\/", i) for i in x], []) if a != '.']))
        return dataset

    def _prune_non_snps(self):
        """
            Remove snps not present in the VCF (monomorphic sites)
            Also will remove sites that are all missing.
        """
        non_snps = self.GT.apply(lambda x: len(set(x[~np.isnan(x)])) > 1)
        return self[non_snps]

    def _prune_alleles(self):
        """
            Remove ANN that are not present in the set of subset samples
        """
        self['allele_set'] = self.TGT.apply(lambda x: set([a for a in sum([re.split("\||\/", i) for i in x], []) if a != '.']))
        self[~self.ANN.isna()].ANN = self[~self.ANN.isna()].apply(lambda row: [i for i in row['ANN'] if i[0] in row.allele_set], axis=1)
        return self

    def subset_samples(self, samples, prune_non_snps=True, inplace=False):
        """
            Subset samples
        """
        sample_bool_keep = np.isin(self.samples, samples)
        df = self.copy()
        # Subset GT
        df.GT = df.GT.apply(lambda row: row[sample_bool_keep])
        df.TGT = df.TGT.apply(lambda row: row[sample_bool_keep])
        df.DP = df.DP.apply(lambda row: row[sample_bool_keep])
        df.FT = df.FT.apply(lambda row: row[sample_bool_keep])

        # Update variables
        df.num_hom_ref = df.GT.apply(lambda row: np.sum(row == 0))
        df.num_het = df.GT.apply(lambda row: np.sum(row == 1))
        df.num_hom_alt = df.GT.apply(lambda row: np.sum(row == 2))
        df.num_missing = df.TGT.apply(lambda row: np.sum(np.isin(row, ['./.', '.|.'])))
        df.missing_rate = df.num_missing
        # Do not change '==' to 'is'; numpy doesn't use 'in'.
        df.num_called = df.TGT.apply(lambda row: np.sum(np.isin(row, ['./.', '.|.']) == False))
        df.call_rate = df.GT.apply(lambda row: np.sum(row != 3)/row.size)

        if prune_non_snps and len(samples) > 1:
            if len(samples) == 1:
                self.messages.append("Subsetting on one sample - not pruning monomorphic SNPs.")
            original_size = df.size
            df = df._prune_non_snps()
            pruned_snps = original_size - df.size
            self.messages.append(f"Pruned SNPs: {pruned_snps}")

        # Update samples
        df.samples = self.samples[np.isin(self.samples, samples)]

        if inplace:
            self.samples = df.samples
            self = df
        else:
            return df

    def _parse_interval(interval):
        """
            Parses an interval
        """
        chrom, *pos = re.split(":-", interval)
        if len(pos) not in [0, 2]:
            raise Exception("Invalid interval")
        elif len(pos) == 2:
            pos = list(map(int, pos))
            return chrom, pos[0], pos[1]
        return chrom, None, None

    #def interval(self, interval):
    #    """
    #        Filters a VCF on an interval
    #    """
    #    chrom, start, end = self._parse_interval(interval)
    #    if chrom and start and end:
    #        query_string = f"CHROM == '{chrom}' & POS > {start} & POS < {end}"
    #    elif chrom:
    #        query_string = f"CHROM == '{chrom}'"
    #    return self.query(query_string)

    def interval_summary(self, interval=None, deep=False):
        """
            Generates a comprehensive interval summary
            Args:
                interval - Act on an interval
                deep - add extra info
        """
        if interval:
            df = self.interval(interval)
        else:
            df = self

        results = infinite_dict()

        # Impact
        impact = results['variants']['impact']
        impact['total'] = Counter(sum(df.ANN.impact.dropna(), []))
        impact['unique'] = Counter(sum(df.ANN.impact.dropna().apply(lambda x: list(set(x))), []))

        # FILTER summary
        impact = results['variants']['impact']
        impact['total'] = Counter(sum(df.ANN.impact.dropna(), []))
        impact['unique'] = Counter(sum(df.ANN.impact.dropna().apply(lambda x: list(set(x))), []))

        # Summary
        variants = results['variants']

        variants['filters']['FILTER'] = Counter(df.FILTER.dropna())
        FT_vals = np.concatenate(df.FT.values)

        if deep:
            # These operations take too long.
            variants['filters']['FT']['combined'] = Counter(FT_vals)
            variants['filters']['FT']['separate'] = Counter(np.concatenate(Series(FT_vals).apply(lambda x: x.split(";")).values))

        # snp
        variants['snp']['records'] = sum(df.is_snp)
        variants['snp']['num_missing'] = sum(df[df.is_snp].num_missing)
        variants['snp']['avg_call_rate'] = np.average(df[df.is_snp].call_rate)
        variants['snp']['transition'] = sum(df[df.is_snp].is_transition)
        variants['snp']['transversion'] = sum(df[df.is_snp].is_transition == False)
        variants['snp']['num_hom_ref'] = sum(df[df.is_snp].num_hom_ref)
        variants['snp']['num_het'] = sum(df[df.is_snp].num_het)
        variants['snp']['num_hom_alt'] = sum(df[df.is_snp].num_hom_alt)

        # indel
        variants['indel']['records'] = sum(df.is_indel)
        variants['indel']['num_missing'] = sum(df[df.is_indel].num_missing)
        variants['indel']['avg_call_rate'] = np.average(df[df.is_indel].call_rate)
        variants['indel']['transition'] = sum(df[df.is_indel].is_transition)
        variants['indel']['transversion'] = sum(df[df.is_indel].is_transition == False)
        variants['indel']['num_hom_ref'] = sum(df[df.is_indel].num_hom_ref)
        variants['indel']['num_het'] = sum(df[df.is_indel].num_het)
        variants['indel']['num_hom_alt'] = sum(df[df.is_indel].num_hom_alt)

        # biotype summary
        variants['biotype'] = Counter(sum(df.ANN.transcript_biotype.dropna().apply(lambda x: list(set(x))), []))

        # By Gene
        gene = results['gene']

        # Gene count
        gene['genes_w_variants'] =len(set(sum(df.ANN.gene_id.dropna().values, [])))

        for impact in set(sum(df.ANN.impact.dropna().values, [])):
            gene['impact'][impact] = list(set(sum(df[df.ANN.impact == impact].ANN.gene_id.dropna().values, [])))

        for transcript_biotype in set(sum(df.ANN.transcript_biotype.dropna().values, [])):
            gene['transcript_biotype'][transcript_biotype] = list(set(sum(df[df.ANN.transcript_biotype == transcript_biotype].ANN.gene_id.dropna().values, [])))

        # Biotype+Impact counts
        for impact in set(sum(df.ANN.impact.dropna().values, [])):
            for transcript_biotype in set(sum(df.ANN.transcript_biotype.dropna().values, [])):
                filter_crit = (df.ANN.impact == impact) & (df.ANN.transcript_biotype == transcript_biotype)
                gene['impact-biotype'][impact][transcript_biotype] = list(set(sum(df[filter_crit].ANN.gene_id.dropna().values, [])))

        # Genes
        return json.dumps(results)


    def interval_summary_table(self):
        df = self
        genes = pd.read_csv("genes.tsv.gz")
        interval_genes = genes[(genes.chrom == df.chrom) & (genes.start > df.start) & (genes.end < df.end) ]
        biotypes_set = list(set(sum(df.ANN.transcript_biotype.dropna().values, [])))

        for biotype in biotypes_set:
            df[biotype] = df.ANN.transcript_biotype == biotype

        df['gene_id'] = df.ANN.gene_id.dropna().apply(lambda x: list(set(x))[0])

        ALL_gene_count = interval_genes[['biotype', 'gene_id']].groupby(['biotype'], as_index=False) \
                                                               .agg(['count'])
        ALL_gene_count = flatten_cols(ALL_gene_count).rename(index=str, columns={"gene_id_count": "gene_count"}) \
                                                     .reset_index()

        GENE_count = df[biotypes_set + ['gene_id']].groupby(['gene_id']) \
                                                   .agg(['max']) \
                                                   .agg(['sum']) \
                                                   .transpose() \
                                                   .reset_index() \
                                                   .rename(index=str, columns={"sum": "genes_w_variants", "level_0": "biotype"}) \
                                                   .drop("level_1", axis=1)

        LMH_set = []
        for x in ["MODIFIER", "LOW", "MODERATE", "HIGH"]:
            lmh_df = df[biotypes_set + ['gene_id']][df.ANN.impact == x].groupby(['gene_id']) \
                                               .agg(['max']) \
                                               .agg(['sum']) \
                                               .transpose() \
                                               .reset_index() \
                                               .rename(index=str, columns={"sum": f"genes_w_{x}_variants", "level_0": "biotype"}) \
                                               .drop("level_1", axis=1)
            LMH_set.append(lmh_df)


        VARIANT_count = df[biotypes_set].agg(['sum']) \
                                        .transpose() \
                                        .reset_index() \
                                        .rename(index=str, columns={"sum": "variants", "index": "biotype"}) 

        dfs = [ALL_gene_count, GENE_count] + LMH_set + [VARIANT_count]
        merged = reduce(lambda left, right: pd.merge(left, right, how='outer', on='biotype'), dfs)
        merged.iloc[:,1:] = merged.iloc[:,1:].fillna(0).astype(int)
        merged['interval'] = df.interval
        return merged.sort_values('variants', ascending=False)


    @staticmethod
    def _sub_values(row, find, replace):
        """
            Substitute values in an array
        """
        np.place(row, row == find, replace)
        return row

    def concordance(self):
        """
            Calculate the concordance of genotypes across all samples.

            Currently functions with ploidy == 1 or 2

            A homozygous REF (e.g. AA) and heterozygous (AG) call
            are treated as dicordant.
        """
        df = self

        # Convert GT to float so nan values can be
        # added.
        df.GT = df.GT.apply(lambda row: row.astype(float)) \
                     .apply(lambda row: self._sub_values(row, 3.0, np.nan))

        called_gtypes = sum(df.GT.apply(lambda row: np.isnan(row) == False))

        # cf
        cf = sum(df.GT.apply(lambda row: (row[:, None] == row)))
        cf = DataFrame(cf, columns=df.samples, index=df.samples)
        cf.index.name = "sample_a"
        cf.columns.name = "sample_b"
        cf = cf.stack()
        cf = DataFrame(cf, columns=['concordant_gt']).reset_index()
        n_called_a = pd.DataFrame(called_gtypes, columns=['gt_called_a'], index=df.samples)
        n_called_b = pd.DataFrame(called_gtypes, columns=['gt_called_b'], index=df.samples)
        n_called_a.index.name = 'sample_a'
        n_called_b.index.name = 'sample_b'
        cf = cf.join(n_called_a, on='sample_a').join(n_called_b, on='sample_b')

        cf['minimum_gt'] = cf.apply(lambda row: min(row.gt_called_a, row.gt_called_b), axis=1)
        cf['concordance'] = cf['concordant_gt'] / cf['minimum_gt']

        return cf

    def hard_filter(self):
        """
            The hard filter method does two things:
                (1) Removes all columns where
                    FILTER != PASS (which is represented as None in pandas-vcf)
                (2) Sets FT (genotype-level) variants to NaN.
        """
        df = self

        df.GT = df.GT.apply(lambda row: row.astype(float)) \
                     .apply(lambda row: self._sub_values(row, 3.0, np.nan)) \

        # Format genotypes and filters.
        GT_filter = np.vstack(df.FT.apply(lambda row: row != "PASS").values)
        GT_vals = np.vstack(df.GT.apply(lambda row: row.astype(float)).values)

        # Apply nan filter to FT != PASS
        GT_vals[GT_filter] = np.nan

        # Re-integrate genotypes
        df.GT = Series(list(GT_vals))

        # FILTER columns
        df = df[df.FILTER.isnull()]

        return df

    def to_fasta(self, filename=None):
        """
            Generates a FASTA file
        """
        df = self
        for sample, row in zip(df.samples, np.vstack(df.TGT.values).T):
            print(f">{sample}")
            seq = Series(row).apply(lambda row: np.str.replace(row, "|", "/")) \
                             .apply(lambda row: np.str.split(row, "/")) \
                             .apply(lambda row: row[0] if len(set(row)) == 1 else "N")
            print(''.join(seq.values).replace(".", "N"))

