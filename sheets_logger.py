import json
import os
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_HK_TZ = timezone(timedelta(hours=8))

# Fixed column positions (1-indexed) — independent of whatever header labels
# are actually displayed in the sheet, so headers can be freely relabeled
# (e.g. translated) without touching this code.
_COL_TIMESTAMP = 1
_COL_CLASSTYPE = 2
_COL_NAME = 3
_COL_PHONE = 4
_COL_AMOUNT = 5
_COL_BILLNUMBER = 6
_COL_QRPAYLOAD = 7
_COL_STATUS = 8

STATUS_ACTIVE = "現用"
STATUS_PAID = "已付"
STATUS_CANCELLED = "取消"


def _get_worksheet():
    creds_json = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
    sheet_id = os.environ["SHEET_ID"]
    credentials = Credentials.from_service_account_info(
        json.loads(creds_json), scopes=_SCOPES
    )
    client = gspread.authorize(credentials)
    return client.open_by_key(sheet_id).sheet1


def log_request(class_type: str, name: str, phone: str, amount: float, bill_number: str, qr_payload: str) -> None:
    """Cancels any existing Active row for the same phone+name, then appends
    a new Active row for this request. Rows already marked Paid are left
    untouched."""
    worksheet = _get_worksheet()
    rows = worksheet.get_all_values()[1:]  # skip header row

    for i, row in enumerate(rows):
        row_number = i + 2  # +1 for 1-indexing, +1 for the header row
        row_phone = row[_COL_PHONE - 1] if len(row) >= _COL_PHONE else ""
        row_name = row[_COL_NAME - 1] if len(row) >= _COL_NAME else ""
        row_status = row[_COL_STATUS - 1] if len(row) >= _COL_STATUS else ""
        if row_phone == phone and row_name == name and row_status == STATUS_ACTIVE:
            worksheet.update_cell(row_number, _COL_STATUS, STATUS_CANCELLED)

    timestamp = datetime.now(_HK_TZ).strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row(
        [timestamp, class_type, name, phone, amount, bill_number, qr_payload, STATUS_ACTIVE]
    )
