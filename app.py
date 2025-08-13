from flask import Flask, request, jsonify
import os
import logging
from datetime import datetime

app = Flask(__name__)

# Setup logging so you can see SafeSend calls in Render logs
logging.basicConfig(level=logging.INFO)

# Load API key from Render environment variables
API_KEY = os.environ.get("SAFESEND_API_KEY", "Your_SafeSend_API_Key")

@app.route("/safesend-return", methods=["GET", "POST"])
def safesend_return():
    app.logger.info(f"Received {request.method} request at /safesend-return")
    app.logger.info(f"Headers: {dict(request.headers)}")

    # GET request = Test Connection (SafeSend sometimes does GET here)
    if request.method == "GET":
        app.logger.info("Responding to SafeSend Test Connection (GET)")
        return jsonify({"status": "Webhook is live"}), 200

    # For POST requests, check x-api-key header
    incoming_key = request.headers.get("x-api-key")
    if incoming_key != API_KEY:
        app.logger.warning(f"Unauthorized request - bad x-api-key: {incoming_key}")
        return "Unauthorized", 401

    # Log JSON payload
    data = request.get_json(silent=True) or {}
    app.logger.info(f"Payload received: {data}")

    # Handle Test Connection eventType=0
    if data.get("eventType") == 0:
        app.logger.info("SafeSend Test Connection received (POST)")
        return jsonify({"status": "Test connection successful"}), 200

    # Handle Download ESign Document eventType=1000
    if data.get("eventType") == 1000:
        app.logger.info("Download ESign Document event received")
        # Example: Save payload to file with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        with open(f"/tmp/safesend_event_{timestamp}.json", "w") as f:
            import json
            json.dump(data, f, indent=2)
        return jsonify({"status": "Document processing started"}), 200

    # Handle Return Status Changed eventType=1001
    if data.get("eventType") == 1001:
        app.logger.info("Return Status Changed event received")
        return jsonify({"status": "Return status processed"}), 200

    # Default for unknown events
    return jsonify({"status": "Event processed"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
