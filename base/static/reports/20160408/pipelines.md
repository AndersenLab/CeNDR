# Methods / Pipelines

__Note__: These methods operated on sequence data at the isotype level.

## Software

### Alignment

Sequences were aligned to WS245 using [BWA](http://bio-bwa.sourceforge.net/) (version 0.7.8-r455). Optical/PCR duplicates were marked with PICARD (version 1.111).

### Variant Calling

SNV calling was performed using [bcftools](http://www.htslib.org/) (version 1.3). 

### Filtering

Sites with greater than 10% missing or greater than 90% heterozygous calls across all isotypes were removed. 
Individual calls with the following parameters were removed:

* Depth of coverage (DP) <= 10
* Quality (QUAL) < 30
* Mapping Quality (MQ) < 40. Only applied to ALT calls.
* Number of high-quality non-reference bases (DV) / Depth of Coverage (DP) < 0.5. Applied only to ALT calls.

### Annotation

Variants were annotated using [SnpEff](http://snpeff.sourceforge.net/) (version 4.1g) using the WS241 database. 

# Pipelines

The _C. elegans_ Natural Diversity Resource has three git repos which contain the software used to run the site.

## [AndersenLab/cegwas](https://www.github.com/Andersenlab/cegwas)

A set of functions to process phenotype data, perform GWAS, and perform post-mapping data processing for _C. elegans_.

## [AndersenLab/cegwas-worker](https://www.github.com/Andersenlab/cegwas-worker)

A python daemon that handles submitted mapping jobs from base. `cegwas-worker` Runs on [Google Compute Engine](https://cloud.google.com/compute/). 

## [AndersenLab/CeNDR](https://www.github.com/Andersenlab/CeNDR)

The software responsible for this website, which is run using [Google App Engine](https://cloud.google.com/appengine/).