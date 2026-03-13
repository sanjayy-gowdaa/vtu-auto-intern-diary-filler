# Internshipyet Auto Diary Filler

Automate the process of filling out your internship diary with dynamically generated, realistic entries using the Gemini API. This bot is tailored to automate the student internship diary entries by generating description, learnings, and resolving common API authentication steps.

## Setup Instructions

1. **Install Dependencies**
   Ensure you have the required Python packages installed to avoid missing module errors:
   ```bash
   pip install requests google-genai pydantic python-dotenv
   ```

2. **Configure Environment Variables**
   - Copy `.env.example` to a new file named `.env`.
   - Open `.env` and fill in your details:
     - `ACCESS_TOKEN` & `REFRESH_TOKEN`: Your valid authorization tokens from the browser session.
     - `TARGET_INTERNSHIP_ID`: The ID corresponding to your internship.
     - `START_DATE` & `END_DATE`: The date range for processing (format: YYYY-MM-DD).
     - `GEMINI_API_KEY`: Your Gemini API key from Google AI Studio.
     - `DELAY_BETWEEN_APPLIES`: Seconds to wait in between requests to API endpoints.

3. **Run the Script**
   ```bash
   python bot.py
   ```

---

## ⚠️ Important Warnings

- ⚠️ **Token Expiration**: Access tokens expire periodically. If you see "TOKEN EXPIRED" error, get a new token from your browser.
- ⚠️ **Rate Limiting**: The script includes delays between requests. Adjust `DELAY_BETWEEN_APPLIES` if needed.
- ⚠️ **HTTP 429 Error**: Running the script for extended periods may trigger HTTP 429 (Too Many Requests) errors due to potential DDoS protection. Take breaks between runs if this occurs. **WARNING: If you reduce the wait time drastically, you risk triggering DDoS attack protection mechanisms or getting permanently blocked.**
- ⚠️ **Use Responsibly**: This tool is for personal use. Don't abuse the platform's API.
