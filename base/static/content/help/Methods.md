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