import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from base.constants import GOOGLE_SHEETS


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


def get_google_sheet(google_sheet_key, worksheet):
    """
        In order for this to work you must share the worksheet with the travis service-account. 
        cendr-travis-ci@andersen-lab.iam.gserviceaccount.com
        
        Note that the GOOGLE_SHEET dict is used above and expects the key to match the worksheet.
    """
    gsheet = authenticate_google_sheets()
    return gsheet.open_by_key(google_sheet_key).worksheet(worksheet)


def get_google_order_sheet():
    """
        Return the google orders spreadsheet
    """
    return get_google_sheet(GOOGLE_SHEETS['orders'], 'orders')


def add_to_order_ws(row):
    """
        Stores order info in a google sheet.
    """
    ws = get_google_order_sheet()
    index = sum([1 for x in ws.col_values(1) if x]) + 1

    header_row = filter(len, ws.row_values(1))
    values = []
    for x in header_row:
        if x in row.keys():
            values.append(row[x])
        else:
            values.append("")

    row = map(str, row)
    ws.insert_row(values, index)


def lookup_order(invoice_hash):
    """
        Lookup an order by its hash
    """
    ws = get_google_order_sheet()
    find_row = ws.findall(invoice_hash)
    print(ws)
    if len(find_row) > 0:
        row = ws.row_values(find_row[0].row)
        header_row = ws.row_values(1)
        result = dict(zip(header_row, row))
        return {k: v for k, v in result.items() if v}
    else:
        return None

