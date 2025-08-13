import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify

app = Flask(__name__)

# Read environment variables
API_KEY = os.environ.get("API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO", "").split(",")
EMAIL_FROM = os.environ.get("EMAIL_FROM")
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

def send_email(to_addresses, subject, body):
    """Send an email using SMTP."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(to_addresses)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, to_addresses, msg.as_string())

@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    # Authenticate
    incoming_key = request.headers.get("x-api-key")
    if incoming_key != API_KEY:
        print("❌ Authentication failed. Invalid API key.")
        return jsonify({"status": "error", "message": "Invalid API key"}), 401

    # Get JSON payload
    data = request.get_json()
    if not data:
        print("❌ No JSON payload received.")
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    print(f"📩 Received webhook payload: {data}")

    # Email details
    subject = f"SafeSend Return Status Changed - {data.get('status')}"
    body = (
        f"Status: {data.get('status')}\n"
        f"Status Date: {data.get('statusDate')}\n"
        f"Form Type: {data.get('formType')}\n"
        f"Tax Year: {data.get('taxYear')}\n"
        f"Client ID: {data.get('clientId')}\n"
        f"Document ID: {data.get('documentId')}\n"
        f"Document GUID: {data.get('documentGuid')}"
    )

    # Log email details before sending
    print(f"📧 Attempting to send email to: {EMAIL_TO}")
    print(f"📧 Email subject: {subject}")
    print(f"📧 Email body: {body}")

    try:
        send_email(EMAIL_TO, subject, body)
        print("✅ Email send function completed without error.")
    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return jsonify({"status": "error", "message": f"Email send failed: {e}"}), 500

    return jsonify({"status": "success"}), 200

@app.route("/", methods=["GET"])
def home():
    return "SafeSend Webhook is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
