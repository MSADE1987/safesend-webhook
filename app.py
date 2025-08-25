import os
import base64
import json
import requests
from flask import Flask, request, jsonify

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

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

def send_via_graph(to_emails, subject, body, attachments=None):
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

    if attachments:
        message["message"]["attachments"] = attachments

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = SENDMAIL_URL.format(sender=GRAPH_SENDER)
    r = requests.post(url, headers=headers, data=json.dumps(message), timeout=30)

    if r.status_code in (200, 202):
        print("✅ Email sent via Microsoft Graph")
        return True
    print(f"❌ Graph send error {r.status_code}: {r.text}")
    return False

def download_file_from_sas(sas_url, filename):
    try:
        r = requests.get(sas_url, timeout=30)
        if r.status_code == 200:
            path = os.path.join(DOWNLOAD_DIR, filename)
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"📥 Downloaded: {filename}")
            return path, r.content
        else:
            print(f"❌ Failed to download {filename}: {r.status_code}")
    except Exception as e:
        print(f"❌ Error downloading {filename}: {e}")
    return None, None

@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    data = request.get_json(silent=True) or {}
    print("📩 Received webhook payload:", data)

    event_type = data.get("eventType")

    if event_type == 0:
        print("🔍 Test connection event received.")
        return jsonify({"message": "Test connection successful"}), 200

    # Common data
    status = data.get("status") or "UNKNOWN"
    form_type = data.get("formType", "")
    tax_year = data.get("taxYear", "")
    client_id = data.get("clientId", "")
    document_id = data.get("documentId", "")
    document_guid = data.get("documentGuid", "")

    subject = f"SafeSend Return Status Changed - {status}"
    body = (
        f"Status: {status}\n"
        f"Form Type: {form_type}\n"
        f"Tax Year: {tax_year}\n"
        f"Client ID: {client_id}\n"
        f"Document ID: {document_id}\n"
        f"Document GUID: {document_guid}\n"
    )

    attachments = []

    if event_type == 1000:
        print("📦 Document Download Event triggered")

        files = data.get("signedEFiles", []) + data.get("additionalESignedFiles", [])
        for f in files:
            name = f.get("fileName")
            url = f.get("fileSAS")
            if name and url:
                local_path, file_bytes = download_file_from_sas(url, name)
                if file_bytes:
                    attachments.append({
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": name,
                        "contentType": "application/pdf",
                        "contentBytes": base64.b64encode(file_bytes).decode("utf-8"),
                    })

        if not files:
            body += "\n(No documents found in payload.)"

    if not EMAIL_TO:
        print("⚠️ EMAIL_TO not set; skipping email.")
        return jsonify({"message": "Processed", "email": "skipped"}), 200

    ok = send_via_graph(EMAIL_TO, subject, body, attachments=attachments)
    return jsonify({"message": "Processed", "email": "sent" if ok else "failed"}), 200

@app.route("/", methods=["GET"])
def home():
    return "SafeSend Webhook (Graph) is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
