# AI-Powered Email Campaign Manager

A Flask web application that classifies contact lists using Google Gemini and delivers email campaigns via Resend's API.

## Live Deployment
- **Live URL**: https://emailpro-campaign-manager.onrender.com

## Features
- **AI Recipient Segmentation**: Uses Gemini 2.5 Flash to classify email addresses into Business or Individual domains.
- **REST Delivery Pipeline**: Direct integration with Resend API for reliable transactional email delivery over HTTPS.
- **Audience Management**: Ingests audience lists via CSV and provides downloadable delivery status reports.

## Tech Stack
- Python, Flask, Gunicorn
- Google GenAI SDK (`gemini-2.5-flash`)
- Resend API
- Render (PaaS Hosting)
