import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials



# WI Strain Info Dataset
GOOGLE_SHEETS = {"orders": "1BCnmdJNRjQR3Bx8fMjD_IlTzmh3o7yj8ZQXTkk6tTXM",
                 "WI": "1V6YHzblaDph01sFDI8YK_fP0H7sVebHQTXypGdiQIjI"}




def get_service_account_credentials():
    """
        Fetch service account credentials for google sheets
    """
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


def get_google_sheet(google_sheet):
    # In order for this to work you must share the worksheet with the travis service-account. 
    # cendr-travis-ci@andersen-lab.iam.gserviceaccount.com
    # Note that the GOOGLE_SHEET dict is used above and expects the key to match the worksheet.
    gsheet = authenticate_google_sheets()
    return gsheet.open_by_key(GOOGLE_SHEETS[google_sheet]).worksheet(google_sheet)