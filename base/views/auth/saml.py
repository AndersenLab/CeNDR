import arrow

from flask import (redirect,
									url_for,
									session,
									request,
									make_response,
                  flash,
									Blueprint)
from slugify import slugify
from base.models import user_ds
from base.utils.jwt import assign_access_refresh_tokens

from urllib.parse import urlparse
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils


saml_bp = Blueprint('saml',
                    __name__,
                    template_folder='')

pd = {
  'eduPersonPrincipalName': 'urn:oid:1.3.6.1.4.1.5923.1.1.1.6',
  'mail': 'urn:oid:0.9.2342.19200300.100.1.3',
  'o': 'urn:oid:2.5.4.10',
  'displayName': 'urn:oid:2.16.840.1.113730.3.1.241',
  'uid':  'urn:oid:0.9.2342.19200300.100.1.1',
}


def get_or_register_user(saml_auth):
  try:
    attributes = saml_auth.get_attributes()
    username = attributes[pd.get('eduPersonPrincipalName')]
    username = username[0]
    id = slugify(username)
    if id is None:
      return None

    user = user_ds(id)
    now = arrow.utcnow().datetime
    if not user._exists:
      user.created_on = now
      user.roles = ['user']

    user.username = username
    user.email = attributes[pd['mail']]
    user.verified_email = True
    user.o = attributes[pd['o']] if hasattr(attributes, pd['o']) else ['']
    user.full_name = attributes[pd['displayName']] if hasattr(attributes, pd['displayName']) else ['']
    user.uid = attributes[pd['uid']] if hasattr(attributes, pd['uid']) else ['']

    # properties are initially arrays
    user.email = user.email[0]
    user.o = user.o[0]
    user.full_name = user.full_name[0]
    user.uid = user.uid[0]

    # store the rest of the saml info
    user.samlUserdata = attributes
    user.samlNameId = saml_auth.get_nameid()
    user.samlNameIdFormat = saml_auth.get_nameid_format()
    user.samlNameIdNameQualifier = saml_auth.get_nameid_nq()
    user.samlNameIdSPNameQualifier = saml_auth.get_nameid_spnq()
    user.samlSessionIndex = saml_auth.get_session_index()
    user.last_login = now
    user.save()
    return user
  except:
    return None

def init_saml_auth(req):
  """
      Loads the saml config from settings.json 
      to generate the SAML XML
  """
  saml_auth = OneLogin_Saml2_Auth(req, custom_base_path=f"env_config/saml")
  return saml_auth


def prepare_flask_request(request):
  """
      Preprocesser for request data
  """
  # If server is behind proxys or balancers use the HTTP_X_FORWARDED fields
  url_data = urlparse(request.url)
  return {
    'https': 'on' if request.scheme == 'https' else 'off',
    'http_host': request.host,
    'server_port': url_data.port,
    'script_name': request.path,
    'get_data': request.args.copy(),
    # Uncomment if using ADFS as IdP, https://github.com/onelogin/python-saml/pull/144
    # 'lowercase_urlencoding': True,
    'post_data': request.form.copy()
  }


@saml_bp.route('/sso2', methods=['GET', 'POST'])
def saml_sso2():
  """
      Single Sign On (2) route for SAML which includes user attributes
  """
  req = prepare_flask_request(request)
  saml_auth = init_saml_auth(req)
  return_to = session.get("login_referrer")
  return redirect(saml_auth.login(return_to))


@saml_bp.route('/acs', methods=['GET', 'POST'])
def saml_acs():
  """
      Assertion Consumer Service route for SAML
  """
  req = prepare_flask_request(request)
  saml_auth = init_saml_auth(req)
  settings = saml_auth.get_settings()
  errors = []
  error_reason = None
  is_auth = False

  request_id = None
  if 'AuthNRequestID' in session:
    request_id = session['AuthNRequestID']

  saml_auth.process_response(request_id=request_id)
  errors = saml_auth.get_errors()
  is_auth = saml_auth.is_authenticated()

  if (len(errors) == 0) and is_auth:
    if 'AuthNRequestID' in session:
      del session['AuthNRequestID']

    user = get_or_register_user(saml_auth)
    if user is None:
      flash('Failed to retrieve attributes from Identity Provider', 'error')
      return redirect(url_for('auth.logout'))

    self_url = OneLogin_Saml2_Utils.get_self_url(req)
    referrer = session.get("login_referrer",'/')
    if 'RelayState' in request.form and self_url != request.form['RelayState']:
      referrer = request.form['RelayState']
      
    return assign_access_refresh_tokens(user.name, user.roles, referrer)

  elif settings.is_debug_active():
    error_reason = saml_auth.get_last_error_reason()

  flash('Wrong username or password', 'error')
  return redirect(request.referrer)


@saml_bp.route('/metadata/')
def saml_metadata():
  """
      Generates metadata.xml for SAML Service Provider from settings.json
  """
  req = prepare_flask_request(request)
  saml_auth = init_saml_auth(req)
  settings = saml_auth.get_settings()
  metadata = settings.get_sp_metadata()
  errors = settings.validate_metadata(metadata)

  if len(errors) == 0:
    resp = make_response(metadata, 200)
    resp.headers['Content-Type'] = 'text/xml'
  else:
    resp = make_response(', '.join(errors), 500)
  return resp

