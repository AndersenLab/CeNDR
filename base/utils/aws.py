#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

Code for fetching AWS clients

"""

import boto3
from flask import g
from base.utils.gcloud import get_item

def get_aws_client(service='ecs'):
    """
        Retrieve AWS task account
    """
    if not hasattr(g, service):
        fargate_credentials = get_item('credential', 'aws_fargate')
        fargate_credentials.pop("_exists")
        setattr(g, service, boto3.client(service, **fargate_credentials))
    return getattr(g, service)
