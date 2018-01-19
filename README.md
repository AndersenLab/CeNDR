[![Build Status](https://travis-ci.org/AndersenLab/CeNDR.svg?branch=master)](https://travis-ci.org/AndersenLab/CeNDR)

# CeNDR

`CeNDR` is the code used to run the [_Caenorhabditis elegans_ Natural Diversity Resource](https://www.elegansvariation.org) website.

![cendr website](https://storage.googleapis.com/elegansvariation.org/static/img/misc/screenshot.png)

## Building docker container

```bash
docker build -t cendr .
```

## Running the docker container

```bash
docker run -it --publish 5000:8080 cendr
```
