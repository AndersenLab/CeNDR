# CeNDR Database

This directory contains the scripts to perform the 'initdb' flask action.
It requires a local PostgreSQL instance to be running.

The table can then be dumped with

'''
pg_dump -U admin --format=plain --no-owner --no-acl cendr > cendr.sql

'''

The .sql file can then be uploaded to Google Cloud Buckets and  batch imported to the Cloud SQL instance
