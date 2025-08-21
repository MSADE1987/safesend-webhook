import os
import smtplib
from flask import Flask, request, jsonify
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# Environment variables (set in Render)
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 25
SMTP_USERNAME = os.getenv("SMTP_USERNAME")  # full Microsoft 365 email
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # password or app password
EMAIL_TO = os.getenv("EMAIL_TO", "").split(",")  # comma-separated list

# ------------------ Email Sending Function ------------------ #
def send_email(to_emails, subject, body):
    msg = MIMEMultipart()
    msg["From"] = SMTP_USERNAME
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        print(f"📧 Connecting to SMTP server {SMTP_SERVER}:{SMTP_PORT}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            print("🔒 Starting TLS...")
            server.starttls()
            print("🔑 Logging in...")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print(f"📨 Sending email to {to_emails}...")
            server.sendmail(SMTP_USERNAME, to_emails, msg.as_string())
            print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# ------------------ Webhook Endpoint ------------------ #
@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    data = request.get_json()
    print("📩 Received webhook payload:", data)

    event_type = data.get("eventType")
    status = data.get("status", "")
    form_type = data.get("formType", "")
    tax_year = data.get("taxYear", "")
    client_id = data.get("clientId", "")
    document_id = data.get("documentId", "")
    document_guid = data.get("documentGuid", "")

    # Handle Test Connection
    if event_type == 0:
        print("🔍 Test connection event received.")
        return jsonify({"message": "Test connection successful"}), 200

    # Build email content
    subject = f"SafeSend Return Status Changed - {status}"
    body = (
        f"Status: {status}\n"
        f"Form Type: {form_type}\n"
        f"Tax Year: {tax_year}\n"
        f"Client ID: {client_id}\n"
        f"Document ID: {document_id}\n"
        f"Document GUID: {document_guid}\n"
    )

    if EMAIL_TO:
        send_email(EMAIL_TO, subject, body)
    else:
        print("⚠️ No EMAIL_TO configured in environment variables — skipping email send.")

    return jsonify({"message": "Processed"}), 200

# ------------------ Home Page ------------------ #
@app.route("/", methods=["GET"])
def home():
    return "SafeSend Webhook is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
