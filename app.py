import os
import json
import base64
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
import resend
from email_classifier import classify_emails_with_gemini

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

SESSION_DATA = {
    "recipients": [],
    "logs": []
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "Empty file provided"}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        df = pd.read_csv(filepath)
        email_col = next((c for c in df.columns if 'email' in str(c).lower()), None)
        if not email_col:
            return jsonify({"error": "No column containing 'email' found in CSV"}), 400

        emails = df[email_col].dropna().astype(str).str.strip().unique().tolist()
        emails = [e for e in emails if '@' in e]

        SESSION_DATA["recipients"] = [
            {"email": e, "category": "Unclassified", "status": "Pending"} 
            for e in emails
        ]
        SESSION_DATA["logs"].append(f"Loaded {len(emails)} recipients from {file.filename}")

        return jsonify({
            "message": f"Loaded {len(emails)} recipients",
            "count": len(emails),
            "recipients": SESSION_DATA["recipients"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/classify', methods=['POST'])
def classify():
    if not SESSION_DATA["recipients"]:
        return jsonify({"error": "No recipients uploaded yet"}), 400

    email_list = [r["email"] for r in SESSION_DATA["recipients"]]
    categories = classify_emails_with_gemini(email_list)

    biz_count = 0
    ind_count = 0
    for r in SESSION_DATA["recipients"]:
        r["category"] = categories.get(r["email"], "Individual")
        if r["category"] == "Business":
            biz_count += 1
        else:
            ind_count += 1

    SESSION_DATA["logs"].append(f"Classified: {biz_count} Business, {ind_count} Individual")

    return jsonify({
        "business_count": biz_count,
        "individual_count": ind_count,
        "recipients": SESSION_DATA["recipients"]
    })

@app.route('/api/send-campaign', methods=['POST'])
def send_campaign():
    target = str(request.form.get('target', 'All')).strip().lower()
    subject = request.form.get('subject', 'Update from our team')
    body = request.form.get('body', '')

    resend_api_key = os.getenv("RESEND_API_KEY")
    if not resend_api_key:
        return jsonify({"error": "RESEND_API_KEY environment variable is not configured"}), 500

    resend.api_key = resend_api_key

    raw_recipients = request.form.get('recipients')
    recipients_data = []
    if raw_recipients:
        try:
            recipients_data = json.loads(raw_recipients)
        except Exception:
            recipients_data = SESSION_DATA.get("recipients", [])
    else:
        recipients_data = SESSION_DATA.get("recipients", [])

    filtered = []
    for r in recipients_data:
        cat = str(r.get("category", "")).strip().lower()
        if "all" in target:
            filtered.append(r)
        elif "ind" in target and "ind" in cat:
            filtered.append(r)
        elif ("bus" in target or "biz" in target) and ("bus" in cat or "biz" in cat):
            filtered.append(r)
        elif cat == target:
            filtered.append(r)

    if not filtered:
        return jsonify({"error": "No recipients match the selected segment"}), 400

    attachments_payload = []
    if 'attachment' in request.files:
        att = request.files['attachment']
        if att and att.filename:
            raw_bytes = att.read()
            attachments_payload.append({
                "filename": att.filename,
                "content": base64.b64encode(raw_bytes).decode('utf-8')
            })

    sent_count = 0
    fail_count = 0

    for r in filtered:
        try:
            params = {
                "from": "onboarding@resend.dev",
                "to": [r["email"]],
                "subject": subject,
                "text": body,
            }
            if attachments_payload:
                params["attachments"] = attachments_payload

            resend.Emails.send(params)
            r["status"] = "Delivered"
            sent_count += 1
        except Exception:
            r["status"] = "Failed"
            fail_count += 1

    SESSION_DATA["recipients"] = recipients_data
    SESSION_DATA["logs"].append(f"Campaign '{subject}' finished: {sent_count} sent, {fail_count} failed.")

    return jsonify({
        "status": "success",
        "delivered": sent_count,
        "failed": fail_count,
        "recipients": recipients_data
    })

@app.route('/api/export', methods=['GET'])
def export_csv():
    if not SESSION_DATA["recipients"]:
        return jsonify({"error": "No data available to export"}), 400

    df = pd.DataFrame(SESSION_DATA["recipients"])
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], "campaign_report.csv")
    df.to_csv(export_path, index=False)

    return send_file(export_path, as_attachment=True, download_name="campaign_report.csv")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))