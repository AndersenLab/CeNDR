import gspread
from base.application import app
from base.utils.auth import authenticate_google_sheets
from flask import g


# WI Strain Info Dataset
GOOGLE_SHEETS = {"orders": "1BCnmdJNRjQR3Bx8fMjD_IlTzmh3o7yj8ZQXTkk6tTXM",
                 "WI": "1V6YHzblaDph01sFDI8YK_fP0H7sVebHQTXypGdiQIjI"}


def get_google_sheet(google_sheet):
    # In order for this to work you must share the worksheet with the travis service-account. 
    # cendr-travis-ci@andersen-lab.iam.gserviceaccount.com
    # Note that the GOOGLE_SHEET dict is used above and expects the key to match the worksheet.
    gsheet = authenticate_google_sheets()
    return gsheet.open_by_key(GOOGLE_SHEETS[google_sheet]).worksheet(google_sheet)