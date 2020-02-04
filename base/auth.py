import requests
import arrow
from flask import (redirect,
                   render_template,
                   url_for,
                   session,
                   request,
                   flash)
from base.application import app
from functools import wraps
from base.models2 import user_m
from base.utils.data_utils import unique_id
from slugify import slugify
from logzero import logger

from flask import Flask, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.contrib.github import make_github_blueprint, github
from flask_dance.consumer import oauth_authorized

google_bp = make_google_blueprint(scope=["profile", "email"])
github_bp = make_github_blueprint()


@app.route("/login/select", methods=['GET'])
def choose_login(error=None):
    VARS = {'page_title': 'Choose Login'}
    if error:
        flash(error, 'danger')
    return render_template('login.html', **VARS)


@oauth_authorized.connect
def authorized(blueprint, token):
    if google.authorized:
        user_info = google.get("/oauth2/v2/userinfo")
        user_info = {'google': user_info.json()}
        user_email = user_info['google']['email'].lower()
    elif github.authorized:
        user_info = {'github': github.get('/user').json()}
        logger.info(user_info['github'])
        if not user_info['github'].get('email'):
            flash('Please set a public email address in github', 'error')
            return redirect(url_for('choose_login'))
        user_email = user_info['github']['email'].lower()
    else:

        flash("Error logging in!")
        return redirect(url_for("choose_login"))

    #Create or get existing user.
    logger.info(user_email)
    user = user_m(user_email)
    if not user._exists:
        user.user_email = user_email
        user.user_info = user_info
        user.email_confirmation_code = unique_id()
        user.user_id = unique_id()[0:8]
        user.username = slugify("{}_{}".format(user_email.split("@")[0], unique_id()[0:4]))

    user.last_login = arrow.utcnow().datetime
    user.save()

    session['user'] = user
    logger.info(session)

    flash("Successfully logged in!", 'success')
    return redirect(url_for('primary.primary'))

def login_required(f):
    @wraps(f)
    def func(*args, **kwargs):
        if not session.get('user'):
            with app.app_context():
                session['redirect_url'] = request.url
                return redirect(url_for('choose_login'))
        return f(*args, **kwargs)
    return func

@app.route('/logout')
def logout():
    """
        Logs the user out.
    """
    session.clear()
    print(session)
    flash("Successfully logged out", "success")
    return redirect(request.referrer)
