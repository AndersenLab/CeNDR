#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook



"""
import markdown
from flask import Markup, render_template_string
import os


def render_markdown(filename, directory="base/static/content/markdown"):
    with open(os.path.join(directory, filename)) as f:
        template = render_template_string(f.read(), **locals())
        return Markup(markdown.markdown(template))
