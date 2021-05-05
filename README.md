### GOLANG CloudRun for H2 Heritability calculations. ###

Server listens for CloudTask queue requests, downloads the input data from CloudStorage, executes R script, then uploads the result to CloudStorage. At each stage, the DataStore status is updated.

Build using:

gcloud builds submit --config cloudbuild.yaml . --timeout=3h
gcloud run deploy --image gcr.io/andersen-lab/h2-1 --memory 1024Mi --platform managed h2-1 --timeout=15m
