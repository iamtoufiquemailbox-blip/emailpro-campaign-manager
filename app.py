import json

@app.route('/api/send-campaign', methods=['POST'])
def send_campaign():
    target = request.form.get('target', 'All').strip().lower()
    subject = request.form.get('subject', '')
    body = request.form.get('body', '')
    attachment = request.files.get('attachment')

    # Parse recipients sent directly from the client
    raw_recipients = request.form.get('recipients')
    recipients_data = []
    if raw_recipients:
        try:
            recipients_data = json.loads(raw_recipients)
        except Exception:
            recipients_data = []

    # Fallback to global/session contacts if not passed
    if not recipients_data and 'contacts' in globals():
        recipients_data = contacts

    # Filter recipients safely
    targets = []
    for r in recipients_data:
        cat = str(r.get('category', '')).strip().lower()
        if 'all' in target or cat == target:
            targets.append(r)

    if not targets:
        return jsonify({'error': 'No recipients match selected segment'}), 400

    # Dispatch emails via SMTP
    delivered_count = 0
    failed_count = 0

    for r in targets:
        recipient_email = r.get('email')
        try:
            send_email_smtp(recipient_email, subject, body, attachment)
            r['status'] = 'Delivered'
            delivered_count += 1
        except Exception as e:
            r['status'] = 'Failed'
            failed_count += 1

    return jsonify({
        'delivered': delivered_count,
        'failed': failed_count,
        'recipients': recipients_data
    })