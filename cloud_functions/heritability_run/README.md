This directory contains the code to start the Google Cloud Run Microservice for the Heritability Tool

Build using:

```bash
gcloud builds submit --tag gcr.io/andersen-lab/h2 --timeout=3h
gcloud run deploy --image gcr.io/andersen-lab/h2 --memory 512Mi --platform managed h2
```