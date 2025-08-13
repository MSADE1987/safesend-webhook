from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime

app = Flask(__name__)

# Configure logging so we can see incoming webhook requests in Render logs
logging.basicConfig(level=logging.INFO)

# Test connection endpoint — SafeSend will call this when you hit "Test Connection"
@app.route("/", methods=["GET", "POST"])
def root():
    app.logger.info("SafeSend test connection hit")
    return jsonify({"status": "Webhook is live"}), 200

# Actual webhook endpoint SafeSend should call when a return is signed
@app.route("/webhook", methods=["POST"])
def safesend_webhook():
    data = request.json
    app.logger.info(f"Received SafeSend webhook data: {data}")

    # Save incoming data to a local file (temporary on Render's ephemeral filesystem)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"/tmp/safesend_payload_{timestamp}.json"
    with open(filename, "w") as f:
        import json
        json.dump(data, f, indent=2)

    # Here is where you could later:
    # - Download the signed return file from SafeSend's provided URL
    # - Save to cloud or local file server
    # - Trigger email notification

    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    # Render automatically sets PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
