import io
import os
import re

from flask import Flask, request, send_file
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from werkzeug.middleware.proxy_fix import ProxyFix

import sheets_logger
from fps_qr import build_fps_qr, generate_qr_image
from message_parser import parse_request

app = Flask(__name__)
# Trust X-Forwarded-Proto/Host from the tunnel (ngrok) or reverse proxy, so
# request.url_root/request.url reflect the public https:// URL instead of the
# local http:// connection. Twilio refuses to fetch media over plain http,
# and signature verification below needs the URL Twilio actually signed.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

FPS_ID = "116566704"
MERCHANT_NAME = "Stanford Swim School HK"

# Latest generated QR PNG bytes per sender, served back to Twilio via /qr/<key>.png
QR_STORE: dict[str, bytes] = {}


def _sender_key(from_number: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", from_number) or "anon"


def _is_valid_twilio_request() -> bool:
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token:
        return False
    validator = RequestValidator(auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    return validator.validate(request.url, request.form.to_dict(), signature)


@app.post("/whatsapp")
def whatsapp_webhook():
    if not _is_valid_twilio_request():
        return "Invalid signature", 403

    from_number = request.values.get("From", "")
    body = request.values.get("Body", "")
    key = _sender_key(from_number)

    resp = MessagingResponse()
    msg = resp.message()

    try:
        parsed = parse_request(body)
    except ValueError as e:
        msg.body(str(e))
        return str(resp)

    bill_number = f"{parsed.class_type}-{parsed.name}-{parsed.phone}"[:25]
    payload = build_fps_qr(
        fps_id=FPS_ID,
        merchant_name=MERCHANT_NAME,
        bill_number=bill_number,
        amount=parsed.amount,
    )

    buffer = io.BytesIO()
    generate_qr_image(payload, buffer)
    QR_STORE[key] = buffer.getvalue()

    warning = ""
    try:
        sheets_logger.log_request(
            parsed.class_type, parsed.name, parsed.phone, parsed.amount, bill_number, payload
        )
    except Exception:
        warning = "\n\n⚠️ Not logged to the spreadsheet — please add this row manually."

    qr_url = request.url_root.rstrip("/") + f"/qr/{key}.png"
    msg.body(f"Here's your FPS QR for HKD {parsed.amount:.2f} — {parsed.name}{warning}")
    msg.media(qr_url)

    return str(resp)


@app.get("/qr/<key>.png")
def serve_qr(key: str):
    image_bytes = QR_STORE.get(key)
    if image_bytes is None:
        return "Not found", 404
    return send_file(io.BytesIO(image_bytes), mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
