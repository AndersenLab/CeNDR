import os
import arrow
from flask import (abort,
                  redirect,
                  render_template,
                  session,
                  request,
                  make_response,
                  flash,
                  jsonify,
                  Blueprint)
from slugify import slugify

from base.models import user_ds
from base.forms import basic_login_form
from base.utils.jwt_utils import (create_access_token, 
                            set_access_cookies,
                            get_jwt_identity,
                            jwt_required,
                            assign_access_refresh_tokens,
                            unset_jwt)
from base.config import config

auth_bp = Blueprint('auth',
                    __name__,
                    template_folder='')


@auth_bp.route('/refresh', methods=['GET'])
@jwt_required(refresh=True)
def refresh():
  ''' Refreshing expired Access token '''
  username = get_jwt_identity()
  user = user_ds(username)
  if user._exists:
    referrer = session.get('login_referrer', '/')
    return assign_access_refresh_tokens(username, user.roles, referrer, refresh=False)

  return abort(401)


@auth_bp.route("/login/select", methods=['GET'])
def choose_login(error=None):
  # Relax scope for Google
  referrer = session.get("login_referrer") or ""
  if not referrer.endswith("/login/select"):
    session["login_referrer"] = request.referrer
  os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = "true"
  VARS = {'page_title': 'Choose Login'}
  if error:
    flash(error, 'danger')
  return render_template('select_login.html', **VARS)


@auth_bp.route("/login/basic", methods=["GET", "POST"])
def basic_login():
  title = "Login"
  disable_parent_breadcrumb = True
  form = basic_login_form(request.form)
  if request.method == 'POST' and form.validate():
    username = slugify(request.form.get("username"))
    password = request.form.get("password")
    user = user_ds(username)
    if user._exists:
      if user.check_password(password, config['PASSWORD_SALT']):
        user.last_login = arrow.utcnow().datetime
        user.save()
        referrer = session.get('login_referrer', '/')
        flash('Logged In', 'success')
        return assign_access_refresh_tokens(username, user.roles, referrer)
    flash('Wrong username or password', 'error')
    return redirect(request.referrer)
  return render_template('basic_login.html', **locals())


@auth_bp.route('/logout')
def logout():
  """
      Logs the user out.
  """
  session.clear()
  resp = unset_jwt()
  flash("Successfully logged out", "success")
  return resp
