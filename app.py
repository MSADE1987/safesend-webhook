from flask import Flask, request
import requests, os, smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

API_KEY = "Your_SafeSend_API_Key"  # Must match SafeSend Developer Section
LOCAL_FOLDER = "/opt/render/project/src/signed_returns"  # Render storage path
SAFESEND_BASE_URL = "https://api.safesendreturns.com/v1"
EMAIL_FROM = "noreply@yourfirm.com"
EMAIL_TO = ["team@yourfirm.com"]
SMTP_SERVER = "smtp.yourfirm.com"

@app.route("/safesend-return", methods=["POST"])
def safesend_return():
    if request.headers.get("Authorization") != API_KEY:
        return "Unauthorized", 401

    data = request.json
    event_code = data.get("event")
    return_id = data.get("returnId")

    if event_code in [3, 11] and return_id:
        download_url = f"{SAFESEND_BASE_URL}/returns/{return_id}/signed"
        pdf_response = requests.get(download_url, headers={"Authorization": API_KEY})
        
        if pdf_response.status_code == 200:
            os.makedirs(LOCAL_FOLDER, exist_ok=True)
            file_path = os.path.join(LOCAL_FOLDER, f"{return_id}.pdf")
            with open(file_path, "wb") as f:
                f.write(pdf_response.content)
            
            # Send email
            msg = MIMEText(f"Signed return saved at: {file_path}")
            msg["Subject"] = "SafeSend Signed Return"
            msg["From"] = EMAIL_FROM
            msg["To"] = ", ".join(EMAIL_TO)
            
            with smtplib.SMTP(SMTP_SERVER) as smtp:
                smtp.send_message(msg)
        else:
            return "Download failed", 500

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
