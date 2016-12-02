#! /bin/bash
curl "http://metadata.google.internal/computeMetadata/v1/instance/attributes/run_pipeline" -H "Metadata-Flavor: Google" | /home/danielcook/.pyenv/shims/python
gcloud -q compute instances delete --zone=us-central1-a `hostname`