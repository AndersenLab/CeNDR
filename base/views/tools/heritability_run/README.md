This directory contains the code to start the Google Cloud Run Microservice

Build using:

```bash
gcloud builds submit --tag gcr.io/andersen-lab/h2 --timeout=3h
gcloud run deploy --image gcr.io/andersen-lab/h2 --platform managed h2
```