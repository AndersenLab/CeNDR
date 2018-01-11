#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import markdown
from flask import Markup
import os


def render_markdown(filename, directory="base/static/content/markdown"):
    with open(os.path.join(directory, filename)) as f:
        return Markup(markdown.markdown(f.read()))