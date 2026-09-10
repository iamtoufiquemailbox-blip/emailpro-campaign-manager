import os
import json
from google import genai
from google.genai import types

def classify_emails_with_gemini(emails):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {email: "Individual" for email in emails}

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are an email categorization model. Analyze the following list of email addresses:
    {json.dumps(emails)}

    Classify each email strictly as either "Business" or "Individual".
    - "Business" covers corporate domains, companies, work domains, organizations, and professional addresses.
    - "Individual" covers general personal mailbox providers (gmail.com, yahoo.com, outlook.com, hotmail.com, icloud.com, etc.).

    Return ONLY a single valid JSON object mapping every input email to its category.
    Example:
    {{
      "john@company.com": "Business",
      "sarah@gmail.com": "Individual"
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception:
        results = {}
        for email in emails:
            domain = email.split('@')[-1].lower() if '@' in email else ""
            if domain in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"]:
                results[email] = "Individual"
            else:
                results[email] = "Business"
        return results