#!/usr/bin/bash

gcloud beta functions deploy generate_thumbnails --runtime python37 --trigger-bucket gs://elegansvariation
