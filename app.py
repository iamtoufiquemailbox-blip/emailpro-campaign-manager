import resend

@app.route('/api/send-campaign', methods=['POST'])
def send_campaign():
    target = str(request.form.get('target', 'All')).strip().lower()
    subject = request.form.get('subject', 'Update from our team')
    body = request.form.get('body', '')

    resend.api_key = os.getenv("RESEND_API_KEY")

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
        return jsonify({"error": "No recipients match selected segment"}), 400

    sent_count = 0
    fail_count = 0

    attachments_payload = []
    if 'attachment' in request.files:
        att = request.files['attachment']
        if att and att.filename:
            attachments_payload.append({
                "filename": att.filename,
                "content": list(att.read())
            })

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