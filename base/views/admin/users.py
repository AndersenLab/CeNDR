#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Author: Sam Wachspress

User administration

"""
import arrow
from flask import request, render_template, Blueprint, redirect, url_for

from base.models import user_ds
from base.forms import admin_edit_user_form
from base.utils.jwt import jwt_required, get_jwt, admin_required
from base.utils.gcloud import delete_by_ref


users_bp = Blueprint('users',
                      __name__,
                      template_folder='admin')


@users_bp.route('/', methods=["GET"])
@users_bp.route('/<id>', methods=["GET"])
@admin_required()
def users(id=None):
  if id is None:
    title = 'All'
    users = user_ds().get_all()
    return render_template('admin/users_list.html', **locals())
  else:
    return redirect(url_for('users.users_edit'), id=id)


@users_bp.route('/<id>/edit/', methods=["GET", "POST"])
@admin_required()
def users_edit(id=None):
  if id is None:
    # todo: fix redirect
    return render_template('500.html'), 500

  title = "Edit"
  jwt_csrf_token = (get_jwt() or {}).get("csrf")
  form = admin_edit_user_form(request.form)
  user = user_ds(id)

  if request.method == 'GET':
    form.roles.data = user.roles if hasattr(user, 'roles') else ['user']

  if request.method == 'POST' and form.validate():
    user.roles = request.form.getlist('roles')
    user.modified = arrow.utcnow().datetime
    user.save()
    return redirect(url_for('users.users'))

  # todo: fix redirect here
  return render_template('admin/users_edit.html', **locals())


@users_bp.route('/<id>/delete', methods=["GET"])
@admin_required()
def users_delete(id=None):
  if id is None:
  # todo: fix redirect
    return render_template('500.html'), 500

  delete_by_ref('user', id)
  return redirect(url_for('users.users'))
