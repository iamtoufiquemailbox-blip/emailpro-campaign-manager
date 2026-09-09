import os
import smtplib
from email.message import EmailMessage
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
from dotenv import load_dotenv
from email_classifier import classify_emails_with_gemini

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory storage for the active session
SESSION_DATA = {
    "recipients": [],  # List of dicts: {"email": "...", "category": "...", "status": "Pending"}
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
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        df = pd.read_csv(filepath)
        # Search for any column name containing 'email'
        email_col = next((c for c in df.columns if 'email' in c.lower()), None)
        if not email_col:
            return jsonify({"error": "No 'email' column found in CSV"}), 400

        emails = df[email_col].dropna().unique().tolist()
        
        SESSION_DATA["recipients"] = [{"email": e, "category": "Unclassified", "status": "Pending"} for e in emails]
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
    target = request.form.get('target', 'All')
    subject = request.form.get('subject', 'Update from our team')
    body = request.form.get('body', '')

    smtp_email = os.getenv("SMTP_EMAIL")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    # Filter recipients based on selection
    filtered = [
        r for r in SESSION_DATA["recipients"]
        if target == 'All' or r["category"] == target
    ]

    if not filtered:
        return jsonify({"error": "No recipients match selected segment"}), 400

    sent_count = 0
    fail_count = 0

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(smtp_email, smtp_pass)

        for r in filtered:
            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = smtp_email
            msg['To'] = r["email"]
            msg.set_content(body)

            # Check if user attached a file
            if 'attachment' in request.files:
                att = request.files['attachment']
                if att.filename:
                    msg.add_attachment(
                        att.read(),
                        maintype='application',
                        subtype='octet-stream',
                        filename=att.filename
                    )

            try:
                server.send_message(msg)
                r["status"] = "Delivered"
                sent_count += 1
            except Exception as e:
                r["status"] = "Failed"
                fail_count += 1

        server.quit()
        SESSION_DATA["logs"].append(f"Campaign '{subject}' finished: {sent_count} sent, {fail_count} failed.")

        return jsonify({
            "status": "success",
            "delivered": sent_count,
            "failed": fail_count,
            "recipients": SESSION_DATA["recipients"]
        })
    except Exception as e:
        return jsonify({"error": f"SMTP Connection Failed: {str(e)}"}), 500

@app.route('/api/export', methods=['GET'])
def export_csv():
    if not SESSION_DATA["recipients"]:
        return jsonify({"error": "No data available to export"}), 400

    df = pd.DataFrame(SESSION_DATA["recipients"])
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], "campaign_report.csv")
    df.to_csv(export_path, index=False)

    return send_file(export_path, as_attachment=True, download_name="campaign_report.csv")

if __name__ == '__main__':
    app.run(debug=True, port=5000)