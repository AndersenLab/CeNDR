import requests
import arrow
import os
from flask import (redirect,
                   render_template,
                   url_for,
                   session,
                   request,
                   flash,
                   Markup)
from functools import wraps
from base.models import user_ds
from base.utils.data_utils import unique_id
from slugify import slugify
from logzero import logger

from flask import Flask, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.consumer import oauth_authorized

from flask import Blueprint
auth_bp = Blueprint('auth',
                     __name__,
                     template_folder='')

google_bp = make_google_blueprint(scope=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email"],
                                  offline=True)
github_bp = make_github_blueprint(scope="user:email")
# dropbox_bp = make_dropbox_blueprint()


@auth_bp.route("/login/select", methods=['GET'])
def choose_login(error=None):
    # Relax scope for Google
    if not session.get("login_referrer", "").endswith("/login/select"):
        session["login_referrer"] = request.referrer
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = "true"
    VARS = {'page_title': 'Choose Login'}
    if error:
        flash(error, 'danger')
    return render_template('login.html', **VARS)


@oauth_authorized.connect
def authorized(blueprint, token):
    if google.authorized:
        user_info = google.get("/oauth2/v2/userinfo")
        logger.debug(user_info)
        assert user_info.ok
        user_info = {'google': user_info.json()}
        user_email = user_info['google']['email'].lower()
    elif github.authorized:
        user_emails = github.get("/user/emails")
        user_email = [x for x in user_emails.json() if x['primary']][0]["email"].lower()
        user_info = {'github': github.get('/user').json()}
        user_info['github']['email'] = user_email
    else:
        flash("Error logging in!")
        return redirect(url_for("auth.choose_login"))

    # Create or get existing user.
    logger.info(user_email)
    user = user_ds(user_email)
    logger.debug(user)
    logger.debug(user._exists)
    if not user._exists:
        user.user_email = user_email
        user.user_info = user_info
        user.email_confirmation_code = unique_id()
        user.user_id = unique_id()[0:8]
        user.username = slugify("{}_{}".format(user_email.split("@")[0], unique_id()[0:4]))

    user.last_login = arrow.utcnow().datetime
    logger.debug(user)
    user.save()

    session['user'] = user
    logger.debug(session)

    flash("Successfully logged in!", 'success')
    return redirect(session.get("login_referrer", None) or url_for('primary.primary'))

def login_required(f):
    @wraps(f)
    def func(*args, **kwargs):
        if not session.get('user'):
            with app.app_context():
                session['redirect_url'] = request.url
                return redirect(url_for('auth.choose_login'))
        return f(*args, **kwargs)
    return func

@auth_bp.route('/logout')
def logout():
    """
        Logs the user out.
    """
    session.clear()
    flash("Successfully logged out", "success")
    return redirect(request.referrer)
