import qrcode


def crc16_ccitt_false(data: str) -> str:
    """Calculates EMVCo standard CRC-16/CCITT-FALSE checksum."""
    crc = 0xFFFF
    for byte in data.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def build_fps_qr(
    fps_id: str,
    merchant_name: str,
    bill_number: str | None = None,
    amount: float | None = None,
) -> str:
    # 1. Tag 26: FPS Account Information
    guid = "hk.com.hkicl"
    sub_00 = f"00{len(guid):02d}{guid}"
    sub_02 = f"02{len(fps_id):02d}{fps_id}"
    val_26 = sub_00 + sub_02
    id_26 = f"26{len(val_26.encode('utf-8')):02d}{val_26}"

    # 2. Dynamic vs Static Flag
    is_dynamic = amount is not None
    id_01 = "010212" if is_dynamic else "010211"

    # 3. Clean & Truncate Merchant Name (max 25 chars for safety)
    clean_name = merchant_name[:25]
    id_59 = f"59{len(clean_name.encode('utf-8')):02d}{clean_name}"

    # 4. Assemble Payload
    payload_parts = [
        "000201",    # Payload Format Indicator
        id_01,       # Initiation Method
        id_26,       # FPS Info
        "52045999",  # Valid MCC (5999 = General Merchant)
        "5303344",   # Currency (HKD)
    ]

    # Add Amount (Tag 54) if provided
    if is_dynamic:
        amt_str = f"{amount:.2f}"
        payload_parts.append(f"54{len(amt_str):02d}{amt_str}")

    payload_parts.extend(["5802HK", id_59, "6002HK"])

    # Bill Number (Tag 62, sub-01) — optional. Note: confirmed via testing
    # that HSBC HK's scan-to-pay rejects any QR containing this field while
    # Business Collect merchant registration is still pending on the
    # receiving account, even though it's spec-compliant and accepted by
    # HKICL's own validator app.
    if bill_number:
        clean_bill = bill_number[:25]
        sub_62 = f"01{len(clean_bill.encode('utf-8')):02d}{clean_bill}"
        id_62 = f"62{len(sub_62.encode('utf-8')):02d}{sub_62}"
        payload_parts.append(id_62)

    # 5. Calculate Checksum
    raw_payload = "".join(payload_parts) + "6304"
    return raw_payload + crc16_ccitt_false(raw_payload)


def generate_qr_image(payload: str, destination="fps_qr.png"):
    """Renders the QR code to `destination` (a file path or a writable stream, e.g. BytesIO)."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,  # Mandatory quiet zone border
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(destination, format="PNG" if not isinstance(destination, str) else None)
