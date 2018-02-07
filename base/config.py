#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Setup site

Author: Daniel E. Cook
"""
from base.utils.data_utils import json_encoder

class base_config(object):
    json_encoder = json_encoder
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cendr.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

