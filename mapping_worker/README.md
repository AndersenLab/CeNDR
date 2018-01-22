# Setting up


* gcloud_service.json
* AWS Fargate

This folder contains the code for running the GWA worker on AWS Fargate.

If you cloned the repo you will need to obtain the service credentials from the GCloud console


## Testing


Rebuild and test 
```
REPORT_NAME='test-report'
TRAIT_NAME='yeah'
docker build . -t cegwas-mapping && docker run -it --rm -e REPORT_NAME=${REPORT_NAME} -e TRAIT_NAME=${TRAIT_NAME} -e GOOGLE_APPLICATION_CREDENTIALS=gcloud_fargate.json  cegwas-mapping
```

Test
```
docker run -it --rm -e REPORT_NAME='test-report' -e TRAIT_NAME='yeah1' -e GOOGLE_APPLICATION_CREDENTIALS=gcloud_fargate.json  cegwas-mapping
```