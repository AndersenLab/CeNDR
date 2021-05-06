from functools import wraps
from flask import (request,
                  redirect,
                  abort,
                  url_for,
                  session,
                  make_response)
from flask_jwt_extended import (create_access_token, 
                                create_refresh_token, 
                                set_access_cookies,
                                set_refresh_cookies,
                                unset_jwt_cookies,
                                unset_access_cookies,
                                get_jwt,
                                get_jwt_identity,
                                get_current_user,
                                verify_jwt_in_request,
                                jwt_required)

from base.models import user_ds
from base.extensions import jwt

def assign_access_refresh_tokens(id, roles, url, refresh=True):
  resp = make_response(redirect(url, 302))
  access_token = create_access_token(identity=str(id), additional_claims={'roles': roles})
  set_access_cookies(resp, access_token)
  if refresh:
    refresh_token = create_refresh_token(identity=str(id))
    set_refresh_cookies(resp, refresh_token)
  session['is_logged_in'] = True
  session['is_admin'] = ('admin' in roles)
  return resp


def unset_jwt():
  resp = make_response(redirect('/', 302))
  session["is_logged_in"] = False
  session["is_admin"] = False
  unset_jwt_cookies(resp)
  return resp


def admin_required():
  def wrapper(fn):
    @wraps(fn)
    def decorator(*args, **kwargs):
      verify_jwt_in_request()
      claims = get_jwt()
      if claims["roles"] and ('admin' in claims["roles"]):
        return fn(*args, **kwargs)
      else:
        return abort(401)

    return decorator
  return wrapper


@jwt.user_identity_loader
def user_identity_lookup(sub):
  return sub


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
  id = jwt_data["sub"]
  return user_ds(id)


@jwt.unauthorized_loader
def unauthorized_callback(reason):
  return redirect(url_for('auth.choose_login')), 302


@jwt.invalid_token_loader
def invalid_token_callback(callback):
  # Invalid Fresh/Non-Fresh Access token in auth header
  resp = make_response(redirect(url_for('auth.choose_login')))
  session["is_logged_in"] = False
  session["is_admin"] = False
  unset_jwt_cookies(resp)
  return resp, 302


@jwt.expired_token_loader
def expired_token_callback(_jwt_header, jwt_data):
  # Expired auth header
  session['login_referrer'] = request.base_url
  resp = make_response(redirect(url_for('auth.refresh')))
  unset_access_cookies(resp)
  return resp, 302
