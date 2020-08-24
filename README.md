[![Build Status](https://travis-ci.org/AndersenLab/CeNDR.svg?branch=master)](https://travis-ci.org/AndersenLab/CeNDR)

# CeNDR

`CeNDR` is the code used to run the [_Caenorhabditis elegans_ Natural Diversity Resource](https://www.elegansvariation.org) website.

![cendr website](https://storage.googleapis.com/elegansvariation.org/static/img/misc/screenshot.png)


# Page versions

* `download_tab_isotype_v1.html` -  references the original download table which links to isotype-level bams

* `download_tab_strain_v2.html` -  references the new CeNDR versions which organize sequence data at the strain level.

# Building the static database


## Initializing the database

You can create the CeNDR database by running:

```bash
flask initdb WS276 # Where WS276 is the version of wormbase
```

## Running the docker container

```bash
docker build -t cendr .
GAE_VERSION=`cat .travis.yml  | grep 'export VERSION' | cut -f 2 -d '=' | sed 's/version-//g' | awk '{gsub("-", ".", $0); print}'`
# Doesn't require rebuilding
docker run -it -v $PWD:/home/vmagent/app -e GOOGLE_APPLICATION_CREDENTIALS=client-secret.json -e APP_CONFIG=debug -e GAE_VERSION=${GAE_VERSION} --publish $PORT:$PORT cendr /bin/bash
gunicorn -b :$PORT main:app
```
