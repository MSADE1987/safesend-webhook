import os
import smtplib
from flask import Flask, request, jsonify
from email.mime.text import MIMEText

app = Flask(__name__)

API_KEY = os.environ.get("API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO", "").split(",") if os.environ.get("EMAIL_TO") else []
EMAIL_FROM = os.environ.get("EMAIL_FROM")
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")


def send_email(subject, body):
    if not EMAIL_TO:
        app.logger.warning("No EMAIL_TO set — email not sent.")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

    app.logger.info(f"Email sent to {EMAIL_TO}")


@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    data = request.json
    app.logger.info(f"Received Return Status Changed event: {data}")
    return jsonify({"status": "success"}), 200


    data = request.get_json()
    app.logger.info(f"Received SafeSend payload: {data}")

    # Create email body from payload
    subject = f"SafeSend Event: {data.get('eventType', 'Unknown')}"
    body = f"SafeSend sent the following data:\n\n{data}"

    send_email(subject, body)

    return jsonify({"status": "success"}), 200


@app.route("/", methods=["GET"])
def index():
    return "SafeSend Webhook is running", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
