# Methods / Pipelines

This tab links to the nextflow pipelines used to process wild isolate sequence data.

![](/static/img/overview.drawio.svg)

### FASTQ QC and Trimming
__[andersenlab/trim-fq-nf](https://github.com/andersenlab/trim-fq-nf) -- (<strong>Latest</strong> [d637d0b](https://github.com/AndersenLab/trim-fq-nf/tree/d637d0b))__

Adapters and low quality sequences were trimmed off of raw reads using [fastp (0.20.0)](https://github.com/OpenGene/fastp) and default parameters. Reads shorter than 20 bp after trimming were discarded. 

### __Alignment__

__[andersenlab/alignment-nf](https://github.com/andersenlab/alignment-nf) -- ([1c96b4a](https://github.com/AndersenLab/alignment-nf/tree/1c96b4a))__

Trimmed reads were aligned to _C. elegans_ reference genome (project PRJNA13758 version WS276 from the [Wormbase](https://wormbase.org/)) using `bwa mem` [BWA (0.7.17)](http://bio-bwa.sourceforge.net/). Libraries of the same strain were merged together and indexed by [sambamba (0.7.0)](https://lomereiter.github.io/sambamba/). Duplicates were flagged with [Picard (2.21.3)](https://broadinstitute.github.io/picard/).

Strains with less than 14x coverage were not included in the alignment report and subsequent analyses.

### __Variant Calling__

__[andersenlab/wi-gatk](https://github.com/andersenlab/wi-gatk) -- ([a84ba4f](https://github.com/AndersenLab/wi-gatk/tree/a84ba4f))__

Variants for each strain were called using `gatk HaplotypeCaller`. After the initial variant calling, variants were combined and then recalled jointly using `gatk GenomicsDBImport` and `gatk GenotypeGVCFs` [GATK (4.1.4.0)](https://gatk.broadinstitute.org/hc/en-us/sections/360007279452-4-1-4-0?page=6#articles).

The variants were further processed and filtered with custom-written scripts for [heterozygous SNV polarization](https://github.com/AndersenLab/wi-gatk/blob/master/env/het_polarization.nim), GATK (4.1.4.0), and [bcftools (1.10)](http://samtools.github.io/bcftools/bcftools.html).


<div class='alert alert-warning'>

<strong>Warning</strong><br />

Heterozygous polarization and filtering thresholds were optimized for single nucleotide variants (SNVs).

<br /><br />
Additionally, insertion or deletion (indel) variants less than 50 bp are more reliably called than indel variants greater than this size. In general, indel variants should be considered less reliable than SNVs.
</div>

#### Site-level filtering and annotation

1. __Heterozygous SNV polarization__: Because _C. elegans_ is a selfing species, heterozygous SNV sites are most likely errors. Biallelic heterozygous SNVs were converted to homozygous REF or ALT if we had sufficient evidence for conversion. Only biallelic SNVs that are not on mitochondria DNA were included in this step. Specifically, the SNV was converted if the normalized Phred-scaled likelihoods (PL) met the following criteria (a smaller PL means more confidence). Any heterozygous SNVs that did not meet these criteria were left unchanged.
    * If PL-ALT/PL-REF <= 0.5 and PL-ALT <= 200, convert to homozygous ALT
    * If PL-REF/PL-ALT <= 0.5 and PL-REF <= 200, convert to homozygous REF

2. __Soft filtering__: Low quality sites were flagged but not modified or removed.

    For the __site-level__ soft filter, variant sites that meet the following conditions were flagged as PASS. These stats were computed across all samples for each site.

    * Variant quality (QUAL) > 30 (this filter is very lenient, only three sites failed)
    * Variant quality normalized by read depth (QD) > 20
    * Strand bias of ALT calls: strand odds ratio (SOR) < 5
    * Strand bias of ALT calls: Fisherstrand (FS) < 100
    * Fraction of samples with missing genotype < 95%
    * Fraction of samples with heterozygous genotype after heterozygous site polarization < 10%

    For the __sample-level__ soft filter, genotypes that meet the following filters were flagged as PASS for each site in each sample: 

    * Read depth (DP) > 5
    * Site is not heterozygous

3. __SnpEff Annotation__: The predicted impact of each variant site was annotated with [SnpEff (4.3.1t)](https://pcingola.github.io/SnpEff/SnpEff.html). 

4. For the hard-filtered VCF, low quality sites were modified or removed using the following criteria. 
	
    * For the __site-level__ hard filter, variant sites not flagged as PASS were removed.
	* For the __sample-level__ hard filter, genotypes not flagged as PASS were converted to missing (`./.`), with the exception that heterozygous sites on mitochondria where kept unchanged.

    After the steps above, sites that are invariant (`0/0` or `1/1` across all samples, not counting missing `./.`) were removed. 

5. Variant impacts were then annotated using `bcftools csq`, which takes into consideration nearby variants and annotates variant impacts based on haplotypes.

#### Determination of filter thresholds

We re-examined our filter thresholds for this release. A variant simulation pipeline was used as part of this process:

* __Variant Simulations - __[andersenlab/variant-simulations-nf](https://github.com/andersenlab/variant-simulations-nf)

Please see the [filter optimization report](/static/reports/filter_optimization/20200803_optimization_report.html) for further details.

### __Isotype Assignment__
__[andersenlab/concordance-nf](https://github.com/andersenlab/concordance-nf) -- ([5160f9f](https://github.com/andersenlab/concordance-nf/tree/5160f9f))__

<span class="tooltip-item" data-toggle="tooltip"  data-placement="bottom" title="Isotypes are groups of strains that carry distinct genome-wide haplotypes.">Isotype</span> groups contain strains that are likely identical to each other and were sampled from the same isolation locations. For any phenotypic assay, only the isotype reference strain needs to be scored. Users interested in individual strain genotypes can use the strain-level data.

Strains were grouped into isotypes using the following steps:

1. Using all high quality variants (only SNPs from the hard-filtered VCF) and `bcftools gtcheck`, concordance for each pair of strains was calculated as a fraction of shared variants over the total variants in each pair.
	
2. Strain pairs with concordance > 0.9997 were grouped into the same isotype group. The threshold 0.9997 was determined by:
		
    * Examining the distribution of concordance scores.
    * Capturing similarity between strains to minimize the number of strains that get  assigned to multiple isotype groups.
    * Agreement with the isotype groups in previous releases.

3. The following issues, which were rare, were resolved on a case-by-case basis:

    * If one strain was assigned to multiple isotypes. 
    * If one isotype from previous releases matches to multiple new isotype groups.
    * If one new isotype group contains strains from multiple isotypes from previous releases.
	
When issues arose, the pairwise concordance between all strains within an isotype were examined manually. Strains and isotypes may be re-assigned with the goal that strains within the same isotype group should have high concordance with each other, and strains from different isotype groups should have lower concordance. 

### __Tree Generation__

Trees were generated by converting the hard-filtered VCF to Phylip format using [vcf2phylip (030b8d)](https://github.com/edgardomortiz/vcf2phylip/tree/030b8d). Then, the Phylip format was converted to Stockholm format using [Bioconvert (0.3.0)](https://bioconvert.readthedocs.io/en/master/index.html), which was then used to construct a tree with [QuickTree (2.5)](https://github.com/tseemann/quicktree) using default settings. The trees were plotted with [FigTree (1.4.4)](http://tree.bio.ed.ac.uk/software/figtree/) rooting on the most diverse strain XZ1516.

### __Imputation__

Imputation was not done for this release.
