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

aws ecr get-login --no-include-email --region us-east-1 | bash
docker build -t cegwas-mapping .
docker tag cegwas-mapping:latest "710251016579.dkr.ecr.us-east-1.amazonaws.com/cegwas-mapping:${DATASET_RELEASE}"
docker push "710251016579.dkr.ecr.us-east-1.amazonaws.com/cegwas-mapping:${DATASET_RELEASE}"
```
