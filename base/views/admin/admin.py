from flask import (render_template,
                  Blueprint)
from base.config import config
from base.utils.jwt_utils import admin_required

# Admin blueprint
admin_bp = Blueprint('admin',
                     __name__,
                     template_folder='admin')


@admin_bp.route('/')
@admin_required()
def admin():
  VARS = {"title": "Admin"}
  return render_template('admin/admin.html', **VARS)


@admin_bp.route('/strain_sheet/')
@admin_required()
def admin_strain_sheet():
  title = "Andersen Lab Strain Sheet"
  id = config['ANDERSEN_LAB_STRAIN_SHEET']
  prefix = config['GOOGLE_SHEET_PREFIX']
  sheet_url = '{}/{}'.format(prefix, id)
  return render_template('admin/google_sheet.html', **locals())



@admin_bp.route('/publications/')
@admin_required()
def admin_publications_sheet():
  title = "CeNDR Publications Sheet"
  id = config['CENDR_PUBLICATIONS_STRAIN_SHEET']
  prefix = config['GOOGLE_SHEET_PREFIX']
  sheet_url = '{}/{}'.format(prefix, id)
  return render_template('admin/google_sheet.html', **locals())

