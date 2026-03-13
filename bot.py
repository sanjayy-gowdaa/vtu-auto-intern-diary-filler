import requests
import json
import time
import random
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from google import genai
from pydantic import BaseModel

load_dotenv()

# ================= Configuration ==================

# 1. Your Authentication Tokens
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# 2. Your target Internship ID
TARGET_INTERNSHIP_ID = int(os.getenv("TARGET_INTERNSHIP_ID", "304"))

# 3. Form Data Configuration
# Set the range of dates you want to automatically fill.
# They must be in YYYY-MM-DD format!
START_DATE = os.getenv("START_DATE", "2026-03-01")
END_DATE = os.getenv("END_DATE", "2026-03-13")
DELAY_BETWEEN_APPLIES = int(os.getenv("DELAY_BETWEEN_APPLIES", "5"))

REFERENCE_LINKS = ""              

# 4. Gemini API Configuration
# Get your API key from Google AI Studio (https://aistudio.google.com/)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

class DiaryEntry(BaseModel):
    description: str
    learnings: str
    blockers: str

def generate_diary_content():
    """Uses Gemini API to generate daily diary content tailored to the specific format."""
    prompt = """
    Generate a daily internship diary entry for a student working on an "Android App Development using Gen AI" project.
    
    The output should be extremely brief and professional. Provide the output in these 3 string fields:
    
    1. description: A 2-3 sentence paragraph starting with phrases like "On this day, I focused on...", summarizing the work done on Android UI, AI APIs, Kotlin, testing, bug-fixing, etc.
    2. learnings: 3-4 short bullet points formatted as plain text on new lines. Start each bullet with an action verb (e.g. "Understood module integration in Android apps.\nImproved end-to-end testing skills."). NO Markdown. NO Emojis in this field.
    3. blockers: 1 short sentence describing a mild, realistic blocker (e.g. "Faced minor integration conflicts between modules, resolved through code adjustments."). If none, just provide a mild generic technical blocker that was resolved.
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': DiaryEntry,
             'temperature': 0.7, 
        },
    )
    return response.parsed


# ================= Advanced Config ==================

# WARNING: The exact API endpoint for submitting a diary entry needs to be populated below.
# You can find the exact URL by observing the Network Tab in Chrome Developer Tools while manually submitting an entry ONCE.
SUBMIT_API_URL = "https://vtuapi.internyet.in/api/v1/student/internship-diaries/store"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def verify_token():
    """Verify if the token is valid by fetching the internships."""
    url = "https://vtuapi.internyet.in/api/v1/student/internship-applys?page=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 401:
        print("[-] Access token expired! You need to use the refresh token to get a new access token, or log in again.")
        return False
    response.raise_for_status()
    print("[+] Token works and successfully fetched your internships.")
    return True

def submit_diary_entry(entry_date, is_long_day=False):
    """Submits the diary entry using dynamically generated details from Gemini."""
    
    print("[*] Contacting Gemini API for unique diary content...")
    generated = generate_diary_content()
    
    # Alternate between 2 and 4 hours
    hours_worked = 4 if is_long_day else 2
    
    payload = {
        "internship_id": TARGET_INTERNSHIP_ID,
        "date": entry_date,
        "description": generated.description,
        "hours": hours_worked,
        "links": REFERENCE_LINKS,
        "learnings": generated.learnings,
        "blockers": generated.blockers,
        "skill_ids": ["61", "62"],  # Kotlin is 62
        "mood_slider": 5
    }
    
    print(f"[*] Submitting diary entry to {SUBMIT_API_URL} (Hours: {hours_worked})...")
    try:
        response = requests.post(SUBMIT_API_URL, headers=HEADERS, json=payload)
        
        # Check if successful
        if response.status_code in [200, 201]:
            print("[+] Success!")
            print("Response:", json.dumps(response.json(), indent=2))
        else:
            print(f"[-] Failed with status code: {response.status_code}")
            print("Response text:", response.text)
            print("\nWait! The payload variables might have wrong names. Please check Chrome DevTools Network tab to see the exact payload format.")
            
    except requests.exceptions.RequestException as e:
        print(f"[-] Request Failed: {e}")

def get_date_range(start_date_str, end_date_str):
    """Returns a list of date strings between start_date and end_date (inclusive)."""
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    date_list = []
    current = start
    while current <= end:
        date_list.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    
    return date_list

if __name__ == "__main__":
    print(f"--- Internshipyet Auto Diary Filler ---\n")
    print(f"[*] Preparing to fill diary entries from {START_DATE} to {END_DATE}...")
    
    dates_to_fill = get_date_range(START_DATE, END_DATE)
    
    if verify_token():
        print(f"\n[*] Found {len(dates_to_fill)} days to process.")
        
        for index, current_date in enumerate(dates_to_fill):
            print(f"\n----------------------------------------")
            print(f"[*] Processing Day {index + 1}/{len(dates_to_fill)}: {current_date}")
            
            # Alternate between True and False for the 4 hr / 2 hr toggle
            is_long_day = (index % 2 == 0)
            
            submit_diary_entry(entry_date=current_date, is_long_day=is_long_day)
            
            # Sleep to prevent hitting rate limits or spam block
            if index < len(dates_to_fill) - 1:
                print(f"[*] Waiting {DELAY_BETWEEN_APPLIES} seconds before next request...")
                time.sleep(DELAY_BETWEEN_APPLIES)
                
        print("\n[+] All diary entries submitted successfully!")
    else:
        print("[-] Aborting due to authentication error.")
