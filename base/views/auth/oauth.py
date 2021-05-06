import arrow
from flask import (redirect,
                   url_for,
                   session,
                   flash)
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized

from base.config import config
from base.models import user_ds
from base.utils.data_utils import unique_id
from base.utils.jwt_utils import assign_access_refresh_tokens


google_bp = make_google_blueprint(client_id=config['GOOGLE_CLIENT_ID'], 
                                  client_secret=config['GOOGLE_CLIENT_SECRET'], 
                                  scope=["https://www.googleapis.com/auth/userinfo.profile",
                                    "https://www.googleapis.com/auth/userinfo.email",
                                    "openid"],
                                  offline=True)


def create_or_update_google_user(user_info):
  # Get up-to-date properties
  user_id = user_info['google']['id']
  user_email = user_info['google']['email']
  user_name = user_info['google']['name']
  user = user_ds(user_id)
  now = arrow.utcnow().datetime
  if not user._exists:
    user.roles = ['user']
    user.created_on = now

  # Save updated properties
  user.modified_on = now
  user.last_login = now
  user.set_properties(username=user_email, password=unique_id(), salt=config['PASSWORD_SALT'], full_name=user_name, email=user_email.lower())
  user.verified_email = True;
  user.user_type = 'OAUTH'
  user.save()
  return user


@oauth_authorized.connect
def authorized(blueprint, token):
  if not google.authorized:
    flash("Error logging in!")
    return redirect(url_for("auth.choose_login"))

  user_info = google.get("/oauth2/v2/userinfo")
  assert user_info.ok
  user_info = {'google': user_info.json()}
  user = create_or_update_google_user(user_info)

  flash("Successfully logged in!", 'success')
  return assign_access_refresh_tokens(user.name, user.roles, session.get("login_referrer"))
