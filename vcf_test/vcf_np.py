import os
import warnings
import json
import re
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from cyvcf2 import VCF
from pandas import DataFrame, Series
from logzero import logger
from click import secho


def infinite_dict():
    return defaultdict(infinite_dict)



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


class AnnotationItem(Series):

    @property
    def _constructor(self):
        return AnnotationItem

    @property
    def _constructor_expanddim(self):
        return VCF_DataFrame

    def __eq__(self, other):
        logger.info(self)
        return AnnotationItem(self.apply(lambda row: other in row if type(row) == list else False))

    @property
    def length(self):
        result = self.apply(lambda row: len(row) if type(row) == list else 0)
        return AnnotationItem(data=result)


class AnnotationSeries(Series):
    # https://stackoverflow.com/q/48435082/2615190
    our_column_names = ('ANN')


    def __new__(cls, *args, **kwargs):
        if kwargs.get('name', '') in cls.our_column_names:
            obj = object.__new__(cls)
            obj.__init__(*args, **kwargs)
            return obj
        return pd.Series(*args, **kwargs)


    def __eq__(self, other):
        logger.info(self)
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

    _metadata = ['samples', 'messages']
    messages = []


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
        attrs = ['CHROM',
                 'POS',
                 'ID',
                 'REF',
                 'ALT',
                 'QUAL',
                 'FILTER',
                 #'INFO',
                 'FORMAT',
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

        rows = []
        vcf = VCF(filename, gts012=True)
        for line in vcf(interval):
            var_line = {attr: getattr(line, attr) for attr in attrs if hasattr(line, attr)}
            var_line['FT'] = np.array(line.format("FT"))
            var_line['DP'] = np.array(line.format("DP").flatten(), np.int32)
            var_line['gt_types'] = np.array(line.gt_types, np.int8)
            var_line['gt_bases'] = line.gt_bases
            ANN = line.INFO.get("ANN")
            if ANN:
                var_line['ANN'] = [x.split("|") for x in ANN.split(",")]
            rows.append(var_line)
        dataset = VCF_DataFrame.from_dict(rows)
        # Add num missing column
        dataset['num_missing'] = dataset.gt_bases.apply(lambda row: np.sum(np.isin(row, ['./.', '.|.'])))

        # Use ordered CHROM
        dataset.CHROM = pd.Categorical(dataset.CHROM, ordered=True)

        # Add samples
        dataset.samples = np.array(vcf.samples)

        return dataset


    def n_variants(self, chrom, start, end):
        query_string = f"CHROM == '{chrom}' & POS > {start} & POS < {end}"
        return self.query(query_string).CHROM.count()



    def _prune_non_snps(self):
        """
            Remove snps not present in the VCF (monomorphic sites)
            Also will remove sites that are all missing.
        """
        non_snps = self.gt_types.apply(lambda x: len(np.unique(x)) > 1)
        logger.info(non_snps.size)
        return self[non_snps]


    def subset_samples(self, samples, prune_non_snps=True, inplace=False):
        """
            Subset samples
        """
        sample_bool_keep = np.isin(self.samples, samples)
        df = self.copy()
        # Subset gt_types
        df.gt_types = df.gt_types.apply(lambda row: row[sample_bool_keep])
        df.gt_bases = df.gt_bases.apply(lambda row: row[sample_bool_keep])
        df.DP = df.DP.apply(lambda row: row[sample_bool_keep])
        df.FT = df.FT.apply(lambda row: row[sample_bool_keep])

        # Update variables
        df.num_hom_ref = df.gt_types.apply(lambda row: np.sum(row == 0))
        df.num_het = df.gt_types.apply(lambda row: np.sum(row == 1))
        df.num_hom_alt = df.gt_types.apply(lambda row: np.sum(row == 2))
        df.num_missing = df.gt_bases.apply(lambda row: np.sum(np.isin(row, ['./.', '.|.'])))
        # Do not change '==' to 'is'; numpy doesn't use 'in'.
        df.num_called = df.gt_bases.apply(lambda row: np.sum(np.isin(row, ['./.', '.|.']) == False))
        df.call_rate = df.gt_types.apply(lambda row: np.sum(row != 3)/row.size)


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
            return VCF_DataFrame(df)


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


    def interval(self, interval):
        """
            Filters a VCF on an interval
        """
        chrom, start, end = self._parse_interval(interval)
        if chrom and start and end:
            query_string = f"CHROM == '{chrom}' & POS > {start} & POS < {end}"
        elif chrom:
            query_string = f"CHROM == '{chrom}'"
        return self.query(query_string)


    def genome_summary(self, interval=None):
        """
            Generates a comprehensive interval summary
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
        summary = results['variants']


        summary['filters']['FILTER'] = Counter(df.FILTER.dropna())
        FT_vals = np.concatenate(df.FT.values)
        summary['filters']['FT']['combined'] = Counter(FT_vals)
        summary['filters']['FT']['separate'] = Counter(np.concatenate(Series(FT_vals).apply(lambda x: x.split(";")).values))


        # snp
        summary['snp']['records'] = sum(df.is_snp)
        summary['snp']['num_missing'] = sum(df[df.is_snp].num_missing)
        summary['snp']['avg_call_rate'] = np.average(df[df.is_snp].call_rate)
        summary['snp']['transition'] = sum(df[df.is_snp].is_transition)
        summary['snp']['transversion'] = sum(df[df.is_snp].is_transition)
        summary['snp']['num_hom_ref'] = sum(df[df.is_snp].num_hom_ref)
        summary['snp']['num_het'] = sum(df[df.is_snp].num_het)
        summary['snp']['num_hom_alt'] = sum(df[df.is_snp].num_hom_alt)

        # indel
        summary['indel']['records'] = sum(df.is_indel)
        summary['indel']['num_missing'] = sum(df[df.is_indel].num_missing)
        summary['indel']['avg_call_rate'] = np.average(df[df.is_indel].call_rate)
        summary['indel']['transition'] = sum(df[df.is_indel].is_transition)
        summary['indel']['transversion'] = sum(df[df.is_indel].is_transition)
        summary['indel']['num_hom_ref'] = sum(df[df.is_indel].num_hom_ref)
        summary['indel']['num_het'] = sum(df[df.is_indel].num_het)
        summary['indel']['num_hom_alt'] = sum(df[df.is_indel].num_hom_alt)

        print(json.dumps(results, indent=4, sort_keys=True))
        # Genes
        return json.dumps(results)

    #def __repr__(self, *args, **kwargs):
    #    """
    #        Specialized repr to display warning
    #        messages beneath output data frames
    #    """
    #    super(VCF_DataFrame, self).__repr__(*args, **kwargs)
    #    if self.messages:
    #        for msg in self.messages:
    #            secho(msg, fg='green')
    #    self.messages = []
    #    return ""

    #@property
    #def PASS(self):
    #    return self.apply(lambda row: row.FILTER == "PASS")



v = VCF_DataFrame.from_vcf("WI.20170531.snpeff.vcf.gz", "I:1-10000")

df = v

df.subset_samples(df.samples[0:5])

#v.genome_summary()


