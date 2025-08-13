from flask import Flask, request, jsonify
import os
import logging

app = Flask(__name__)

# Setup logging so you can see Test Connection calls in Render logs
logging.basicConfig(level=logging.INFO)

# Config
API_KEY = os.environ.get("SAFESEND_API_KEY", "Your_SafeSend_API_Key")  # Set in Render Environment tab
SAFESEND_BASE_URL = "https://api.safesendreturns.com/v1"
LOCAL_FOLDER = "/opt/render/project/src/signed_returns"

@app.route("/safesend-return", methods=["GET", "POST"])
def safesend_return():
    # For SafeSend Test Connection (GET request)
    if request.method == "GET":
        app.logger.info("SafeSend Test Connection received (GET request)")
        return jsonify({"status": "Webhook is live"}), 200

    # For actual webhook events (POST request)
    app.logger.info("SafeSend webhook received (POST request)")
    
    if request.headers.get("Authorization") != API_KEY:
        app.logger.warning("Unauthorized request received")
        return "Unauthorized", 401

    data = request.json
    app.logger.info(f"Webhook payload: {data}")

    # Here you could add code to download the signed return PDF from SafeSend
    # and save it to LOCAL_FOLDER or cloud storage, then send an email notification.
    
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
