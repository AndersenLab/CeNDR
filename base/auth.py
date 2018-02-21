import requests
import arrow
from flask import (redirect,
                   render_template,
                   url_for,
                   session,
                   request,
                   flash)
from flask_oauthlib.client import OAuth
from flask_oauthlib.client import OAuthException
from base.application import app
from functools import wraps
from base.utils.email import send_email
from base.utils.gcloud import store_item, get_item
from base.models2 import user_m
from base.utils.data_utils import unique_id
from slugify import slugify
from logzero import logger


oauth = OAuth(app)

github = oauth.remote_app(
    'github',
    consumer_key=app.config['GITHUB_CLIENT_ID'],
    consumer_secret=app.config['GITHUB_CLIENT_SECRET'],
    request_token_params={'scope': 'user:email'},
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)


google = oauth.remote_app(
    'google',
    consumer_key=app.config['GOOGLE_CLIENT_ID'],
    consumer_secret=app.config['GOOGLE_CLIENT_SECRET'],
    request_token_params={
        'scope': ['email', 'https://www.googleapis.com/auth/userinfo.email']
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)


@app.route("/login/select", methods=['GET'])
def choose_login(error=None):
    VARS = {'page_title': 'Choose Login'}
    if error:
        flash(error, 'danger')
    return render_template('login.html', **VARS)


@app.route('/login/github')
def login_github():
    return github.authorize(callback=url_for('authorized',
                                             service_name='github',
                                             _external=True))

@app.route('/login/google')
def login_google():
    return google.authorize(callback=url_for('authorized',
                                             service_name='google',
                                             _external=True))

@app.route('/auth/<string:service_name>', methods=['GET'])
def authorized(service_name):
    logger.info(service_name)
    if service_name not in ['google', 'github']:
        return redirect(url_for('choose_login'))
    try:
        if service_name == 'google':
            resp = google.authorized_response()
        elif service_name == 'github':
            resp = github.authorized_response()
    except OAuthException:
        flash("Unknown error", 'danger')
        return redirect(url_for('choose_login'))

    if resp is None:
        flash("Unknown error", 'danger')
        return redirect(url_for('choose_login'))
    elif resp.get('error'):
        error = resp.get('error')
        flash(error, 'danger')
        return redirect(url_for('choose_login'))

    # No access token
    if resp.get('access_token') is None:
        error = 'Access denied: reason=%s error=%s resp=%s' % (
            request.args['error'],
            request.args['error_description'],
            resp
        )
        flash(error, 'danger')
        return redirect(url_for('choose_login'))


    if service_name == 'github':
        session['github_token'] = (resp['access_token'], '')
        user_info = {'github': github.get('user').data}
        user_email = user_info['github']['email'].lower()
    elif service_name == 'google':
        user_info = requests.get('https://www.googleapis.com/userinfo/email?alt=json&access_token={}'.format(resp['access_token']))
        user_info = {'google': user_info.json()['data']}
        user_email = user_info['google']['email'].lower()
   
    # Create or get existing user.
    user = user_m(user_email)
    if not user._exists:
        user.user_email = user_email
        user.user_info = user_info
        user.email_confirmation_code = unique_id()
        user.user_id = unique_id()[0:8]
        user.username = slugify("{}_{}".format(user_email.split("@")[0], unique_id()[0:4]))
    # Update user with login service
    setattr(user, service_name, True)
    user.last_login = arrow.utcnow().datetime
    user.save()

    session['user'] = user
    logger.info(session)

    flash("Successfully logged in!", 'success')
    return redirect(url_for('primary.primary'))


class incorrect_code(BaseException):
    pass


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')


@google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')


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
