import os
import base64
import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# ----- Graph config from env -----
TENANT_ID       = os.getenv("GRAPH_TENANT_ID")
CLIENT_ID       = os.getenv("GRAPH_CLIENT_ID")
CLIENT_SECRET   = os.getenv("GRAPH_CLIENT_SECRET")
GRAPH_SENDER    = os.getenv("GRAPH_SENDER")
EMAIL_TO        = [e.strip() for e in os.getenv("EMAIL_TO", "").split(",") if e.strip()]
API_KEY         = os.getenv("API_KEY")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
GRAPH_SCOPE = "https://graph.microsoft.com/.default"
SENDMAIL_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"

# ----------- Token + Email Sending ----------- #
def get_graph_token():
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": GRAPH_SCOPE,
        "grant_type": "client_credentials",
    }
    r = requests.post(TOKEN_URL, data=data, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Graph token error {r.status_code}: {r.text}")
    return r.json()["access_token"]

def send_via_graph(to_emails, subject, body, attachment_bytes=None, attachment_name=None):
    token = get_graph_token()
    message = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "from": {"emailAddress": {"address": GRAPH_SENDER}},
            "toRecipients": [{"emailAddress": {"address": e}} for e in to_emails],
        },
        "saveToSentItems": True,
    }

    if attachment_bytes and attachment_name:
        message["message"]["attachments"] = [ {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": attachment_name,
            "contentType": "application/pdf",
            "contentBytes": base64.b64encode(attachment_bytes).decode("utf-8"),
        }]

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.post(SENDMAIL_URL.format(sender=GRAPH_SENDER), headers=headers, data=json.dumps(message), timeout=30)

    if r.status_code in (200, 202):
        print("✅ Email sent via Microsoft Graph")
        return True
    print(f"❌ Graph send error {r.status_code}: {r.text}")
    return False

# ----------- Webhook Handler ----------- #
@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    data = request.get_json(silent=True) or {}
    print("📩 Received webhook payload:", data)

    event_type   = data.get("eventType")
    status       = data.get("status", "")
    form_type    = data.get("formType", "")
    tax_year     = data.get("taxYear", "")
    client_id    = data.get("clientId", "")
    document_id  = data.get("documentId", "")
    document_guid= data.get("documentGuid", "")

    # Test Connection Event
    if event_type == 0:
        print("🔍 Test connection event received.")
        return jsonify({"message": "Test connection successful"}), 200

    # Download signed files if available
    saved_files = []
    signed_files = data.get("signedEFiles", [])
    additional_files = data.get("additionalESignedFiles", [])
    all_files = signed_files + additional_files

    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)

    for file in all_files:
        try:
            file_name = file.get("fileName")
            sas_url = file.get("fileSAS")
            if file_name and sas_url:
                timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                full_name = f"{client_id}_{document_id}_{timestamp}_{file_name}"
                file_path = downloads_dir / full_name

                response = requests.get(sas_url, timeout=20)
                if response.ok:
                    file_path.write_bytes(response.content)
                    saved_files.append(str(file_path))
                    print(f"📥 Downloaded: {file_path}")
                else:
                    print(f"❌ Failed to download {file_name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"⚠️ Error downloading file: {e}")

    # Compose email
    subject = f"SafeSend Return Status Changed - {status}"
    body = (
        f"Status: {status}\n"
        f"Form Type: {form_type}\n"
        f"Tax Year: {tax_year}\n"
        f"Client ID: {client_id}\n"
        f"Document ID: {document_id}\n"
        f"Document GUID: {document_guid}\n\n"
        f"Downloaded Files:\n" + "\n".join(saved_files) if saved_files else "No files downloaded."
    )

    # Send notification email
    if not EMAIL_TO:
        print("⚠️ EMAIL_TO not set; skipping email.")
        return jsonify({"message": "Processed", "email": "skipped"}), 200

    ok = send_via_graph(EMAIL_TO, subject, body)
    return jsonify({"message": "Processed", "email": "sent" if ok else "failed"}), 200

@app.route("/", methods=["GET"])
def home():
    return "SafeSend Webhook (Graph + Downloads) is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
