# Software

The _C. elegans_ Natural Diversity Resource has three git repos which contain the software used to run the site.

## [AndersenLab/cegwas](https://www.github.com/Andersenlab/cegwas)

A set of functions to process phenotype data, perform GWAS, and perform post-mapping data processing for _C. elegans_.

## [AndersenLab/cegwas-worker](https://www.github.com/Andersenlab/cegwas-worker)

A python daemon that handles submitted mapping jobs from base. `cegwas-worker` Runs on [Google Compute Engine](https://cloud.google.com/compute/). 

## [AndersenLab/CeNDR](https://www.github.com/Andersenlab/CeNDR)

The software responsible for this website, which is run using [Google App Engine](https://cloud.google.com/appengine/).