import json
import os
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_HK_TZ = timezone(timedelta(hours=8))

_COLUMNS = [
    "Timestamp",
    "ClassType",
    "Name",
    "Phone",
    "Amount",
    "BillNumber",
    "QRPayload",
    "Status",
]
_STATUS_COL = _COLUMNS.index("Status") + 1  # gspread columns are 1-indexed


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
    records = worksheet.get_all_records()

    for i, record in enumerate(records):
        row_number = i + 2  # +1 for 1-indexing, +1 for the header row
        if (
            str(record.get("Phone", "")) == phone
            and str(record.get("Name", "")) == name
            and record.get("Status") == "Active"
        ):
            worksheet.update_cell(row_number, _STATUS_COL, "Cancelled")

    timestamp = datetime.now(_HK_TZ).strftime("%Y-%m-%d %H:%M:%S")
    worksheet.append_row(
        [timestamp, class_type, name, phone, amount, bill_number, qr_payload, "Active"]
    )
