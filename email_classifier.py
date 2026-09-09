import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def classify_emails_with_gemini(email_list):
    """
    Sends email addresses to Gemini to classify as 'Business' or 'Individual'.
    Returns a dictionary mapping each email to its category.
    """
    prompt = f"""
    Analyze the following list of email addresses and classify each one as either 'Business' (corporate/work email with custom company domain) or 'Individual' (public providers like gmail.com, yahoo.com, outlook.com, hotmail.com).
    
    Email list:
    {json.dumps(email_list)}
    
    Respond STRICTLY with valid JSON in this exact format, with no markdown formatting:
    {{"results": [{{"email": "...", "category": "Business"}}, {{"email": "...", "category": "Individual"}}]}}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        return {item["email"]: item["category"] for item in data.get("results", [])}
    except Exception as e:
        print("Gemini API error:", e)
        # Fallback heuristic if API quota runs out or network fails
        fallback = {}
        common_providers = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
        for email in email_list:
            domain = email.split("@")[-1].lower() if "@" in email else ""
            fallback[email] = "Individual" if domain in common_providers else "Business"
        return fallback