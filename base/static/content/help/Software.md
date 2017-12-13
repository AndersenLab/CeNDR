# Software

The _C. elegans_ Natural Diversity Resource has three git repos which contain the software used to run the site.

## <img src="https://andersenlab.org/assets/img/github-large.jpg" width="50px;" />[AndersenLab/cegwas](https://www.github.com/Andersenlab/cegwas)

A set of functions to process phenotype data, perform GWAS, and perform post-mapping data processing for _C. elegans_.

## <img src="https://andersenlab.org/assets/img/github-large.jpg" width="50px;" />[AndersenLab/cegwas-worker](https://www.github.com/Andersenlab/cegwas-worker)

A python daemon that handles submitted mapping jobs from base. `cegwas-worker` Runs on [Google Compute Engine](https://cloud.google.com/compute/). 

## <img src="https://andersenlab.org/assets/img/github-large.jpg" width="50px;" />[AndersenLab/CeNDR](https://www.github.com/Andersenlab/CeNDR)

The software responsible for this website, which is run using [Google App Engine](https://cloud.google.com/appengine/).