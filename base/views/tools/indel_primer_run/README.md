This directory contains the code to start the Google Cloud Run Microservice for the Indel Primer Tool

Build using:

```bash
gcloud builds submit --tag gcr.io/andersen-lab/indel_primer --timeout=3h
gcloud run deploy --image gcr.io/andersen-lab/indel_primer --platform managed indel-primer
```