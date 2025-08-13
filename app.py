import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Get API key from Render environment variable
API_KEY = os.environ.get("API_KEY")

@app.route("/webhook", methods=["POST"])
def webhook():
    # Check for x-api-key in request headers
    if request.headers.get("x-api-key") != API_KEY:
        app.logger.warning("Unauthorized request - bad x-api-key")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    app.logger.info(f"Received event: {data}")

    # Handle test connection event
    if data.get("eventType") == 0:
        return jsonify({"message": "Test Connection successful"}), 200

    # Handle other event types as needed
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    # For local testing
    app.run(host="0.0.0.0", port=5000)
