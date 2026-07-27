from fps_qr import build_fps_qr, generate_qr_image

# --- Manual usage example ---
# For the interactive version, run app.py (WhatsApp chatbot) instead.
payload_string = build_fps_qr(
    fps_id="109020248",
    merchant_name="Stanford Swim School HK",
    bill_number="July swim fees",
    amount=10.00,  # Leave None for Static QR (Recommended for general FPS)
)

generate_qr_image(payload_string, "stanford_swim_fps.png")
print("QR Code generated successfully!")
