import os
import base64
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
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

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

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

def send_via_graph(to_emails, subject, body, attachment_path=None):
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

    if attachment_path and attachment_path.exists():
        with open(attachment_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
            message["message"]["attachments"] = [{
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": attachment_path.name,
                "contentType": "application/pdf",
                "contentBytes": encoded,
            }]

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = SENDMAIL_URL.format(sender=GRAPH_SENDER)
    r = requests.post(url, headers=headers, data=json.dumps(message), timeout=30)

    if r.status_code in (200, 202):
        print("✅ Email sent via Microsoft Graph")
        return True
    print(f"❌ Graph send error {r.status_code}: {r.text}")
    return False

@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    data = request.get_json(silent=True) or {}
    print("📩 Received webhook payload:", data)

    event_type     = data.get("eventType")
    status         = data.get("status", "")
    form_type      = data.get("formType", "")
    tax_year       = data.get("taxYear", "")
    client_id      = data.get("clientId", "")
    document_id    = data.get("documentId", "")
    document_guid  = data.get("documentGuid", "")
    signed_files   = data.get("signedEFiles", [])

    # Test Connection
    if event_type == 0:
        print("🔍 Test connection event received.")
        return jsonify({"message": "Test connection successful"}), 200

    attachment_path = None
    file_logs = ""
    if signed_files:
        file_info = signed_files[0]  # only download first for now
        url = file_info.get("fileSAS")
        name = file_info.get("fileName", "signed.pdf")
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        filename = f"{client_id}_{document_id}_{timestamp}_{name}"
        attachment_path = DOWNLOAD_DIR / filename

        try:
            print(f"⬇️ Downloading file from {url}...")
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                attachment_path.write_bytes(response.content)
                print(f"✅ Saved to {attachment_path}")
                file_logs = f"\n\nDownloaded Files:\n{attachment_path}"
            else:
                print(f"❌ Failed to download: {response.status_code}")
        except Exception as e:
            print(f"❌ Error downloading file: {e}")

    subject = f"SafeSend Return Status Changed - {status}"
    body = (
        f"Status: {status}\n"
        f"Form Type: {form_type}\n"
        f"Tax Year: {tax_year}\n"
        f"Client ID: {client_id}\n"
        f"Document ID: {document_id}\n"
        f"Document GUID: {document_guid}"
        f"{file_logs}"
    )

    if not EMAIL_TO:
        print("⚠️ EMAIL_TO not set; skipping email.")
        return jsonify({"message": "Processed", "email": "skipped"}), 200

    ok = send_via_graph(EMAIL_TO, subject, body, attachment_path)
    return jsonify({"message": "Processed", "email": "sent" if ok else "failed"}), 200

@app.route("/", methods=["GET"])
def home():
    return "SafeSend Webhook (Graph) is running", 200

@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename):
    return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
