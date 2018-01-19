#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

User profile

"""
from flask import render_template, Blueprint, session
from base.models2 import user_m
from logzero import logger

user_bp = Blueprint('user',
                    __name__)



@user_bp.route('/profile/<string:username>')
def user(username):
    """
        The User Profile
    """
    user_obj = session.get('user')
    VARS = {'title': username,
            'user_obj': user_m(user_obj['name'])}
    return render_template('user.html', **VARS)