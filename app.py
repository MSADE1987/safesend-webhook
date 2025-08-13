from flask import Flask, request, jsonify
import os
import logging

app = Flask(__name__)

# Logging so you can see calls in Render logs
logging.basicConfig(level=logging.INFO)

# Load API key from Render env vars
API_KEY = os.environ.get("SAFESEND_API_KEY", "Your_SafeSend_API_Key")

@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    # Authenticate using SafeSend's header
    incoming_key = request.headers.get("x-api-key")
    if incoming_key != API_KEY:
        app.logger.warning(f"Unauthorized: Received key {incoming_key}")
        return "Unauthorized", 401

    data = request.get_json(silent=True) or {}
    app.logger.info(f"Received payload: {data}")

    # Handle Test Connection (eventType 0)
    if data.get("eventType") == 0:
        app.logger.info("SafeSend Test Connection received")
        return jsonify({"status": "Test connection successful"}), 200

    # Handle signed returns (Download ESign Document eventType 1000)
    if data.get("eventType") == 1000:
        # Here you can grab fileSAS links and download files
        app.logger.info("Download ESign Document event received")
        # TODO: Add PDF download + email notification
        return jsonify({"status": "Document processing started"}), 200

    # Handle Return Status Changed (eventType 1001)
    if data.get("eventType") == 1001:
        app.logger.info("Return Status Changed event received")
        return jsonify({"status": "Return status processed"}), 200

    return jsonify({"status": "Event processed"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
