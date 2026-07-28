# Hong Kong Common QR Code (HKQR) Payload Specification & Implementation Guide

This documentation provides a comprehensive guide to understanding, constructing, and generating **Hong Kong Common QR Code (HKQR)** compliant payloads for accepting **Faster Payment System (FPS)** payments in Hong Kong.

The specification is based on the **EMVCo QR Code Specification for Payment Systems (Merchant-Presented Mode)** and follows a **Type-Length-Value (TLV)** format.

---

## Table of Contents
1. [Overview of TLV Format](#1-overview-of-tlv-format)
2. [Data Payload Fields & Numerical Identifiers](#2-data-payload-fields--numerical-identifiers)
   - [Root-Level Data Objects](#root-level-data-objects)
   - [FPS Merchant Account Information (ID 26)](#fps-merchant-account-information-id-26)
   - [Point of Initiation Flags (ID 01)](#point-of-initiation-flags-id-01)
3. [CRC-16 Checksum Calculation (ID 63)](#3-crc-16-checksum-calculation-id-63)
4. [Example Payload Strings](#4-example-payload-strings)
5. [Developer Integration Guidelines](#5-developer-integration-guidelines)

---

## 1. Overview of TLV Format

Every block of data within an HKQR string is encoded using a 3-part sequence:

$$\text{[2-Digit ID]} + \text{[2-Digit Length]} + \text{[Value]}$$

* **ID (2 digits):** A numeric identifier ranging from `00` to `99` that tells the scanning app what data type follows.
* **Length (2 digits):** Zero-padded numeric value (`01` to `99`) indicating the exact character length of the **Value** string.
* **Value (Variable):** The actual string content (alphanumeric, string, or nested sub-fields).

---

## 2. Data Payload Fields & Numerical Identifiers

### Root-Level Data Objects

Below are the mandatory and optional fields required to build a valid HKQR string:

| ID | Data Object Name | Format | Length | Presence | Value / Rules | Description |
| :---: | :--- | :---: | :---: | :---: | :--- | :--- |
| **`00`** | Payload Format Indicator | Numeric | `02` | **Mandatory** | `01` | Defines the EMVCo template version. Always set to `"01"`. |
| **`01`** | Point of Initiation Method | Numeric | `02` | **Optional** | `11` or `12` | `11` = Static (reusable code).<br>`12` = Dynamic (single transaction). |
| **`26`** | Merchant Account Info (FPS) | Template | Var (up to `99`) | **Mandatory** | *(Nested TLV)* | Reserved specifically for FPS in Hong Kong. Contains reverse domain and your **FPS ID**. |
| **`52`** | Merchant Category Code (MCC) | Numeric | `04` | **Mandatory** | `0000` | ISO 18245 code or dummy fallback `"0000"`. |
| **`53`** | Transaction Currency | Numeric | `03` | **Mandatory** | `344` | ISO 4217 numeric currency code. **`344`** represents Hong Kong Dollar (HKD). |
| **`54`** | Transaction Amount | ANS | Var (up to `13`) | **Conditional** | e.g. `150.00` | Required when `ID 01` = `12` (Dynamic). Omitted for static codes to prompt user entry. |
| **`58`** | Country Code | ANS | `02` | **Mandatory** | `HK` | ISO 3166-1 alpha-2 country code (`HK` for Hong Kong). |
| **`59`** | Merchant Name | ANS | Var (up to `25`) | **Mandatory** | e.g., `MY SHOP` | Your "Doing Business As" (DBA) or registered company name. |
| **`60`** | Merchant City | ANS | Var (up to `15`) | **Mandatory** | `HK` | Physical city location. Default is `HK`. |
| **`63`** | Cyclic Redundancy Check (CRC) | ANS | `04` | **Mandatory** | *(4-Char Hex)* | 16-bit checksum calculated over the entire payload up to `6304`. |

---

### FPS Merchant Account Information (ID 26)

Template `26` wraps two internal **Sub-IDs** to route payments directly to your bank account:

| Sub-ID | Name | Format | Length | Value | Description |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **`00`** | Globally Unique Identifier (GUID) | ANS | `13` | `hk.com.hkicl` | Identifies Hong Kong Interbank Clearing Limited (HKICL) FPS network. Formatted as `0013hk.com.hkicl`. |
| **`02`** | FPS Identifier (FPS ID) | ANS | Var | e.g., `1234567` | Your bank-assigned unique FPS ID. Formatted as `02` + `[Length]` + `[FPS_ID]`. |

#### Example Sub-field Assembly:
* **GUID Sub-field:** `0013hk.com.hkicl` (Length = 13)
* **FPS ID Sub-field:** `02071234567` (Length = 7)
* **Combined Sub-Value:** `0013hk.com.hkicl02071234567` (Total Length = 26)
* **Final ID 26 Object:** `26260013hk.com.hkicl02071234567`

---

### Point of Initiation Flags (ID 01)

* **`010211` (Static QR Code):**
  - Used for printed counter stands or stickers.
  - Omits Transaction Amount (`ID 54`).
  - Prompts customer's banking app to ask the user to type in the amount to pay.
  
* **`010212` (Dynamic QR Code):**
  - Used for POS displays, web checkouts, or dynamic invoices.
  - Requires Transaction Amount (`ID 54`).
  - Pre-fills the payment amount automatically on the customer's banking app.

---

## 3. CRC-16 Checksum Calculation (ID 63)

The payload ends with a **CRC-16/CCITT-FALSE** checksum calculated across the entire string.

### Calculation Parameters:
* **Polynomial:** `0x1021` ($x^{16} + x^{12} + x^5 + 1$)
* **Initial Value:** `0xFFFF`
* **Final XOR Value:** `0x0000`
* **Input Data:** ASCII bytes of the string, starting from `000201...` up to and including `6304` (excluding the 4 checksum characters themselves).

### Procedure:
1. Append `6304` to the end of your assembled payload string.
2. Calculate the 16-bit CRC checksum over the string.
3. Convert the resulting integer to a 4-character uppercase Hexadecimal string (zero-padded if necessary).
4. Append the Hex string to the end of `6304`.

---

## 4. Example Payload Strings

### Example 1: Static QR Code (Prompt User for Amount)
* **FPS ID:** `1234567`
* **Merchant Name:** `MY SHOP`

```text
00020101021126260013hk.com.hkicl020712345675204000053033445802HK5907MY SHOP6002HK63049F2A
```

---

## 5. Project Structure

* **`fps_qr.py`** — Core payload/QR generation logic (`build_fps_qr`, `generate_qr_image`, `crc16_ccitt_false`).
* **`message_parser.py`** — Parses the fixed-format WhatsApp request message into class type, name, phone, and amount.
* **`sheets_logger.py`** — Logs every generated QR to Google Sheets, auto-cancelling any prior unpaid entry for the same customer.
* **`main.py`** — Minimal manual example: generates a single QR PNG to disk using a hardcoded amount and message. Useful for quick one-off testing without WhatsApp.
* **`app.py`** — Flask webhook server that turns QR generation into a WhatsApp chatbot (see below).

---

## 6. WhatsApp Chatbot Setup (Twilio Sandbox)

The chatbot uses the **Twilio WhatsApp Sandbox**, which is free indefinitely for personal/dev use — no Meta Business verification required.

### One-time setup
1. Install dependencies: `pip install -r requirements.txt`
2. Create a free [Twilio account](https://www.twilio.com/try-twilio) and open the **WhatsApp Sandbox** page in the Twilio Console (Messaging → Try it out → Send a WhatsApp message).
3. From your own WhatsApp, send the sandbox's "join `<your-code>`" message to the sandbox number shown in the console. This links your number to the sandbox.
4. Set `TWILIO_AUTH_TOKEN` (from the Twilio Console) as an environment variable — the webhook rejects any request that isn't validly signed by Twilio.

### Running locally
1. Start the Flask server: `python app.py` (listens on port 5000).
2. In a separate terminal, expose it publicly with [ngrok](https://ngrok.com/): `ngrok http 5000`. Copy the `https://...ngrok-free.app` URL it prints.
3. In the Twilio Console's Sandbox settings, set "WHEN A MESSAGE COMES IN" to `https://<your-ngrok-domain>/whatsapp` (method: `HTTP POST`), then save.

### Using it

Send a single message in this fixed format: `<classtype>-<name>-<phone>-<amount>`

```
You:  SG-JohnWong-91234567-15453

Bot:  Here's your FPS QR for HKD 15453.00 — JohnWong
      [QR code image]
```

Note: none of `classtype`, `name`, or `phone` can contain a hyphen themselves, since the message is split into exactly 4 parts on `-`.

The merchant identity (FPS ID and merchant name, set at the top of `app.py`) is fixed. Every request is logged to Google Sheets (see below); if the same phone number + name sends another request while the previous one is still unpaid, the old row is automatically marked `Cancelled` and the new one becomes the active entry — already-`Paid` rows are never touched.

**Note:** Generated QR images are kept in memory per WhatsApp number, so restarting `app.py` clears any not-yet-fetched images (the permanent record lives in the Google Sheet instead).

---

## 7. Google Sheets Logging Setup

Every generated QR is logged to a Google Sheet with columns `Timestamp | ClassType | Name | Phone | Amount | BillNumber | QRPayload | Status`. Setup uses a Google **service account** (no interactive login needed on the server side):

1. In the [Google Cloud Console](https://console.cloud.google.com/), create (or select) a project, then enable the **Google Sheets API** (APIs & Services → Library → search "Google Sheets API" → Enable).
2. Go to **APIs & Services → Credentials → Create Credentials → Service Account**. Give it any name, no special roles needed.
3. Open the new service account → **Keys** tab → **Add Key → Create new key → JSON**. This downloads a `.json` file — treat it like a password, never commit it to git.
4. Create a Google Sheet with a header row: `Timestamp | ClassType | Name | Phone | Amount | BillNumber | QRPayload | Status`. Click **Share**, and share it with the service account's email address (found inside the JSON file, looks like `something@your-project.iam.gserviceaccount.com`) as **Editor**.
5. Set these environment variables (locally in a `.env`, or on your hosting platform's dashboard — never committed to the repo):
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — the **entire contents** of the downloaded JSON file, pasted as one value.
   - `SHEET_ID` — the long ID in the sheet's URL: `docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`.

If the Sheets API call fails for any reason (missing credentials, network issue, etc.), the bot still generates and sends the QR — it just adds a warning to the reply telling you to log that entry manually.