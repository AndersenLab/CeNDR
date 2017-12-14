import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_service_account_credentials():
    return json.loads(open("client-secret.json", 'r').read())


def authenticate_google_sheets():
    """
        Uses service account credentials to authorize access to
        google sheets.

        In order for this to work you must share the worksheet with the
        service account: cendr-travis-ci@andersen-lab.iam.gserviceaccount.com
    """
    service_credentials = get_service_account_credentials()
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(service_credentials, scope)
    return gspread.authorize(credentials)
