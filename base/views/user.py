#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Daniel E. Cook

User profile

"""
from flask import render_template, Blueprint, session, redirect, url_for, flash

from base.models2 import user_m
from logzero import logger

user_bp = Blueprint('user',
                    __name__)



@user_bp.route('/profile/<string:username>')
def user(username):
    """        The User Profile
    """
    user_obj = session.get('user')
    if user_obj is None:
        flash("You must be logged in to view your profile", 'danger')
        return redirect(url_for('primary.primary'))
    VARS = {'title': username,
            'user_obj': user_m(user_obj['name'])}
    return render_template('user.html', **VARS)
