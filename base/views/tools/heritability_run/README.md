This directory contains the code to start the Google Cloud Run Microservice

Build using:

```bash
gcloud builds submit --tag gcr.io/andersen-lab/h2
gcloud run deploy --image gcr.io/andersen-lab/h2 --platform managed
```