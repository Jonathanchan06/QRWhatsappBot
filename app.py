import io
import re

from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
from werkzeug.middleware.proxy_fix import ProxyFix

from fps_qr import build_fps_qr, generate_qr_image

app = Flask(__name__)
# Trust X-Forwarded-Proto/Host from the tunnel (ngrok) or reverse proxy, so
# request.url_root reflects the public https:// URL instead of the local
# http:// connection. Twilio refuses to fetch media over plain http.
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

FPS_ID = "109020248"
MERCHANT_NAME = "Stanford Swim School HK"

# Per-sender conversation state, e.g. {"state": "AWAITING_MESSAGE", "amount": 10.0}
SESSIONS: dict[str, dict] = {}

# Latest generated QR PNG bytes per sender, served back to Twilio via /qr/<key>.png
QR_STORE: dict[str, bytes] = {}


def _sender_key(from_number: str) -> str:
    return re.sub(r"[^0-9A-Za-z]", "", from_number) or "anon"


@app.post("/whatsapp")
def whatsapp_webhook():
    from_number = request.values.get("From", "")
    body = request.values.get("Body", "").strip()
    key = _sender_key(from_number)

    resp = MessagingResponse()
    msg = resp.message()

    if body.lower() in ("cancel", "reset"):
        SESSIONS.pop(key, None)
        msg.body("Cancelled. Send any message to start a new QR request.")
        return str(resp)

    session = SESSIONS.setdefault(key, {"state": "IDLE"})
    state = session["state"]

    if state == "IDLE":
        session["state"] = "AWAITING_AMOUNT"
        msg.body("How much would you like to charge? (e.g. 10.00)")
        return str(resp)

    if state == "AWAITING_AMOUNT":
        try:
            amount = float(body)
            if amount <= 0:
                raise ValueError
        except ValueError:
            msg.body("That doesn't look like a valid amount. Please enter a number, e.g. 10.00")
            return str(resp)

        session["amount"] = amount
        session["state"] = "AWAITING_MESSAGE"
        msg.body("What's the payee message / reference for this payment?")
        return str(resp)

    if state == "AWAITING_MESSAGE":
        if not body:
            msg.body("Please enter a payee message / reference (e.g. 'July swim fees').")
            return str(resp)

        amount = session["amount"]
        # Note: ref_number is intentionally not passed here — HSBC HK's
        # scan-to-pay rejects any QR containing Tag 62 (confirmed via
        # testing), even though it's spec-compliant. The message is still
        # shown in the reply text below, just not embedded in the QR itself.
        payload = build_fps_qr(
            fps_id=FPS_ID,
            merchant_name=MERCHANT_NAME,
            amount=amount,
        )

        buffer = io.BytesIO()
        generate_qr_image(payload, buffer)
        QR_STORE[key] = buffer.getvalue()

        qr_url = request.url_root.rstrip("/") + f"/qr/{key}.png"
        msg.body(f"Here's your FPS QR for HKD {amount:.2f} — {body}")
        msg.media(qr_url)

        SESSIONS.pop(key, None)
        return str(resp)

    # Fallback: shouldn't happen, but reset defensively.
    SESSIONS.pop(key, None)
    msg.body("Something went wrong — send any message to start again.")
    return str(resp)


@app.get("/qr/<key>.png")
def serve_qr(key: str):
    image_bytes = QR_STORE.get(key)
    if image_bytes is None:
        return "Not found", 404
    return send_file(io.BytesIO(image_bytes), mimetype="image/png")


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
