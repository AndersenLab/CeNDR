# Mapping worker

`The mapping worker environment is setup and run as a conda environment in a docker container. The conda environment is specified in env.yml`.

All packages, including `andersenlab/cegwas` are specified using conda. 

# Versioning

The mapping worker version should correspond with the version of CeNDR.

# Building the conda package for cegwas

I had to create a conda package for cegwas. Ultimately this makes installation / building much easier and faster (6 min docker build instead of \~30 minutes or more).

The conda package is located in `/mapping_worker/r-cegwas`

```
cd r-cegwas/
conda build .

# Convert to other platforms
conda convert --platform linux-64 /Users/dec/opt/anaconda3/conda-bld/osx-64/r-cegwas-1.0.2-r35_0.tar.bz2 -o .
anaconda upload /Users/dec/opt/anaconda3/conda-bld/osx-64/r-cegwas-1.0-r35_0.tar.bz2

```

# Setting up


* gcloud_service.json
* AWS Fargate

This folder contains the code for running the GWA worker on AWS Fargate.

If you cloned the repo you will need to obtain the service credentials from the GCloud console
l

## Testing


Rebuild and test 
```shell
DATASET_RELEASE=20180527
REPORT_NAME='dan-test-test4'
TRAIT_NAME='telomere-resids'
docker build . -t cegwas-mapping
docker run -v $PWD:/home/linuxbrew/work \
           -w /home/linuxbrew/work \
           -it \
           --rm \
           -e REPORT_NAME="${REPORT_NAME}" \
           -e TRAIT_NAME="${TRAIT_NAME}" \
           -e DATASET_RELEASE="${DATASET_RELEASE}" \
           -e GOOGLE_APPLICATION_CREDENTIALS=gcloud_fargate.json \
           -e AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
           -e AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
           cegwas-mapping
```

Test
```
docker run -it --rm \
           -e REPORT_NAME="${REPORT_NAME}" \
           -e TRAIT_NAME="${TRAIT_NAME}" \
           -e DATASET_RELEASE="${DATASET_RELEASE}" \
           -e GOOGLE_APPLICATION_CREDENTIALS=gcloud_fargate.json  cegwas-mapping

DATASET_RELEASE=20180527
# Test Run; Mount local
docker run -it --rm \
           -v $(PWD):/home/linuxbrew/work \
           -w /home/linuxbrew/work \
           -e REPORT_NAME="${REPORT_NAME}" \
           -e TRAIT_NAME="${TRAIT_NAME}" \
           -e DATASET_RELEASE="${DATASET_RELEASE}" \
           -e GOOGLE_APPLICATION_CREDENTIALS=gcloud_fargate.json  cegwas-mapping \
           /bin/bash

```

## Pushing new versions

__You should use the dataset release, test first (to make sure it's working!)__

```

DATASET_RELEASE=20180527

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "710251016579.dkr.ecr.us-east-1.amazonaws.com/cegwas-mapping:${DATASET_RELEASE}"
docker build -t cegwas-mapping .
docker tag cegwas-mapping:latest "710251016579.dkr.ecr.us-east-1.amazonaws.com/cegwas-mapping:${DATASET_RELEASE}"
docker push "710251016579.dkr.ecr.us-east-1.amazonaws.com/cegwas-mapping:${DATASET_RELEASE}"
```
