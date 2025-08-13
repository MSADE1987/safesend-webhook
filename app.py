import logging
import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

API_KEY = os.environ.get("API_KEY")
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_TO = os.environ.get("EMAIL_TO").split(",")
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")

@app.route("/webhook", methods=["POST"])
def webhook():
    # Authentication
    if request.headers.get("x-api-key") != API_KEY:
        logging.warning("Unauthorized request - bad x-api-key")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    event_type = data.get("eventType", "Unknown")
    logging.info(f"Received event type: {event_type}")

    # Prepare email
    subject = f"SafeSend Event: {event_type}"
    body = f"Received SafeSend event:\n\n{data}"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    try:
        logging.info(f"Attempting to send email to {EMAIL_TO}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
