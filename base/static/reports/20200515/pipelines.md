# Methods / Pipelines

This tab links to the nextflow pipelines used to process wild isolate sequence data.

![](/static/img/overview.drawio.svg)

### FASTQ QC and Trimming
__[andersenlab/trim-fq-nf](https://github.com/andersenlab/trim-fq-nf) -- (<strong>Latest</strong> [f0b63e](https://github.com/AndersenLab/trim-fq-nf/tree/f0b63e))__

Adapters and low quality sequences were trimmed off of raw reads using fastp (0.20.0) and default parameters. Reads shorter than 20 bp after trimming were discarded. 

### __Alignment__

__[andersenlab/alignment-nf](https://github.com/andersenlab/alignment-nf) -- ([892b37](https://github.com/AndersenLab/alignment-nf/tree/892b37))__

Trimmed reads were aligned to _C. elegans_ reference genome (project PRJNA13758 version WS276 from the Wormbase) using bwa mem (0.7.17). Libraries of the same strain were merged together and indexed by sambamba (0.7.0). Duplicates were flagged with Picard (2.21.3).

Strains with less than 14x coverage were not included in the alignment report and subsequent analyses.

### __Variant Calling__

__[andersenlab/wi-gatk](https://github.com/andersenlab/wi-gatk) -- ([c9dd1e](https://github.com/AndersenLab/wi-gatk/tree/c9dd1e))__

Variants for each strain were called using HaplotypeCaller (GATK 4.1.4.0). After the initial variant calling, variants were combined and then recalled jointly using GenomicsDBImport and GenotypeGVCFs (GATK 4.1.4.0).

The variants were further processed and filtered with custom-written scripts for heterozygous SNV polarization, GATK (4.1.4.0), and bcftools (1.10).


<div class='alert alert-warning'>

<strong>Warning</strong><br />

Heterozygous polarization and filtering thresholds were optimized for single nucleotide variants (SNVs).

<br /><br />
Additionally, Insertion or deletion (indel) variants less than 50 bp are more reliably called than indel variants greater than this size. In general, indel variants should be considered less reliable than SNVs.
</div>

#### Site-level filtering and annotation

1. __Heterozygous SNV polarization__: Because _C. elegans_ is a selfing species, heterozygous SNV sites are most likely errors. Biallelic heterozygous SNVs were converted to homozygous REF or ALT if we had sufficient evidence for conversion. Only biallelic SNVs that are not on mitochondria DNA were included in this step. Specifically, the SNV was converted if the normalized Phred-scaled likelihoods (PL) met the following criteria (a smaller PL means more confidence). Any heterozygous SNVs that did not meet these criteria were left unchanged.
    * If PL-ALT/PL-REF <= 0.5 and PL-ALT <= 200, convert to homozygous ALT
    * If PL-REF/PL-ALT <= 0.5 and PL-REF <= 200, convert to homozygous REF
2. __Soft filtering__: Low quality sites were flagged but not modified or removed.
For the site-level soft filter, variant sites that meet the following conditions were flagged as PASS. These stats were computed across all samples for each site.

    * Variant quality (QUAL) > 30 (this filter is very lenient filter, only three sites failed)
    * Variant quality normalized by read depth (QD) > 20
    * Strand bias of ALT calls: strand odds ratio (SOR) < 5
    * Strand bias of ALT calls: Fisherstrand (FS) < 100
    * Fraction of samples with missing genotype < 95%
    * Fraction of samples with heterozygous genotype after heteterozygous site polarization > 10%

    For the sample-level soft filter, genotypes that meet the following filters were flagged as PASS for each site in each sample: 

    * Read depth (DP) > 5
    * Site is not heterozygous

3. __SnpEff Annotation__: The predicted impact of each variant site was annotated with SnpEff (4.3.1t). 

4. The single strain VCF and tsv files were created with the soft-filtered, SnpEff annotated VCF file.

5. For the hard-filtered VCF, low quality sites were modified or removed using the following criteria. 
	
    * For the site-level hard filter, variant sites not flagged as PASS were removed.
	* For the sample-level hard filter, genotypes not flagged as PASS were converted to missing (`./.`), with the exception that heterozygous sites on mitochondria where kept unchanged.

    After the steps above, sites that are invariant (`0/0` or `1/1` across all samples, not counting missing `./.`) were removed. 

6. Variant impacts were then annotated using `bcftools csq`, which takes into consideration nearby variants and annotates variant impacts based on haplotypes.

#### Determination of filter thresholds

We re-examined our filter thresholds for this release. Please see the [filter optimization report](/static/reports/filter_optimization/20200803_optimization_report.html) for details.

#### __Concordance__
__[andersenlab/concordance-nf](https://github.com/andersenlab/concordance-nf) -- ([ae3d80](https://github.com/andersenlab/concordance-nf/tree/ae3d80))__

<span class="tooltip-item" data-toggle="tooltip"  data-placement="bottom" title="Isotypes are groups of strains that carry distinct genome-wide haplotypes.">Isotype</span> groups contain strains that are likely identical to each other and sampled from the same isolation locations. For any phenotypic assay, only the isotype reference strain needs to be scored. Users interested in individual strain genotypes can use the strain-level data.

Strains were grouped into isotypes using following steps:

1. Using all high quality variants (the `hard-filter` VCF), concordance for each pair of strains was calculated as a fraction of shared variants over the total variants in each pair.
	
2. Strain pairs with concordance > 0.9995 were grouped into the same isotype group. The threshold 0.9995 was determined by:
		
    * Examining the distribution of concordance scores.
    * capturing similarity between strains to minimize the number of strains that get  assigned to multiple isotype groups.
    * agreement with the isotype groups in previous releases.

3. The following issues were resolved on a case-by-case basis. These types of issues are rare.

    * If one strain was assigned to multiple isotypes. 
    * If one existing isotype matches to multiple new isotype groups.
    * If one new isotype group contains strains from multiple existing isotypes.
	
When issues arise, the pairwise concordance between all strains within the isotypes involved were manually examined. Strains and isotypes may be re-assigned with the goal that strains within the same isotype group should have high concordance with each other, and strains from different isotype groups should have lower concordance. 

### Additional Pipelines

* __Variant Simulations - __[andersenlab/variant-simulations-nf](https://github.com/andersenlab/variant-simulations-nf)