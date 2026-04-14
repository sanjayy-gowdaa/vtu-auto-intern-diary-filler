import requests
import json
import time
import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ================= Configuration ==================

# 1. Your Authentication Tokens
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

# 2. Your target Internship ID
TARGET_INTERNSHIP_ID = int(os.getenv("TARGET_INTERNSHIP_ID", "304"))

# 3. Delay between submissions (seconds)
DELAY_BETWEEN_APPLIES = int(os.getenv("DELAY_BETWEEN_APPLIES", "5"))

# 4. Path to your Excel/CSV file (set via env or directly here)
EXCEL_FILE_PATH = os.getenv("EXCEL_FILE_PATH", "diary_entries.xlsx")

# ================= Advanced Config ==================

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


def load_excel_entries(file_path: str) -> list[dict]:
    """
    Loads diary entries from an Excel (.xlsx) or CSV (.csv) file.

    Expected column order (no header row needed):
        date        - MM/DD/YYYY or DD-MM-YYYY  (e.g. 03/21/2026)
        description - Work done that day
        hours       - Number of hours worked  (leave blank to skip the row)
        links       - Reference / meeting links
        learnings   - What was learned
        blockers    - Any blockers (use 'None' if none)
        skill_ids   - Comma-separated skill IDs (e.g. "61,62")

    Rows with a blank 'hours' field are treated as no-session days and skipped.
    Returns a list of dicts ready to pass to submit_diary_entry().
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(file_path, header=None, encoding="cp1252", dtype=str)
    else:
        df = pd.read_excel(file_path, header=None)

    POSITIONAL_COLUMNS = ["date", "description", "hours", "links", "learnings", "blockers", "skill_ids"]

    # If the first row looks like a header (all strings), use it; otherwise assign names by position.
    first_row = df.iloc[0]
    if all(isinstance(v, str) for v in first_row):
        df.columns = [str(v).strip().lower() for v in first_row]
        df = df.iloc[1:].reset_index(drop=True)   # drop the header row from data
    else:
        # No header — check if the first column is a leading index/serial number column
        # (sequential integers, e.g. 1,2,3... or 48,49,50...) and drop it if so.
        first_col = df.iloc[:, 0]
        is_index_col = (
            pd.api.types.is_integer_dtype(first_col)
            and (first_col.diff().dropna() == 1).all()   # values increase by 1 each row
        )
        if is_index_col:
            print(f"[*] Detected leading index column (values {first_col.iloc[0]}–{first_col.iloc[-1]}), skipping it.")
            df = df.iloc[:, 1:].reset_index(drop=True)

        if len(df.columns) < len(POSITIONAL_COLUMNS):
            raise ValueError(
                f"Excel has only {len(df.columns)} column(s) but needs at least {len(POSITIONAL_COLUMNS)}.\n"
                f"Expected column order: {POSITIONAL_COLUMNS}"
            )
        df = df.iloc[:, :len(POSITIONAL_COLUMNS)].copy()
        df.columns = POSITIONAL_COLUMNS

    required_columns = set(POSITIONAL_COLUMNS)
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(
            f"Excel file is missing required columns: {missing}\n"
            f"Found columns: {list(df.columns)}"
        )

    # Drop completely empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    # Forward-fill merged cells (Excel merged cells only have a value in the first cell)
    df = df.ffill()

    entries = []
    for row_num, row in df.iterrows():
        # --- Date ---
        raw_date = row["date"]

        # pandas may already have converted the Excel cell to a Timestamp/datetime
        if isinstance(raw_date, (pd.Timestamp, datetime)):
            parsed_date = pd.Timestamp(raw_date).to_pydatetime()
        else:
            raw_date_str = str(raw_date).strip().split(" ")[0]  # drop any time part
            parsed_date = None
            for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                try:
                    parsed_date = datetime.strptime(raw_date_str, fmt)
                    break
                except ValueError:
                    continue
            if parsed_date is None:
                print(f"[!] Row {row_num + 2}: Cannot parse date '{raw_date_str}' — skipping.")
                continue

        entry_date = parsed_date.strftime("%Y-%m-%d")   # API expects YYYY-MM-DD

        # --- Hours --- (blank = no-session day, skip silently)
        raw_hours = str(row["hours"]).strip()
        if raw_hours in ("", "nan", "none", "NaN"):
            print(f"[*] Row {row_num + 2} ({entry_date}): No hours — no-session day, skipping.")
            continue
        try:
            hours = int(float(raw_hours))
        except (ValueError, TypeError):
            print(f"[!] Row {row_num + 2}: Invalid hours value '{raw_hours}' — skipping.")
            continue

        # --- Skill IDs: API requires integers, e.g. "14,62" → [14, 62] ---
        raw_skills = str(row["skill_ids"]).strip()
        try:
            skill_ids = [int(float(s.strip())) for s in raw_skills.split(",") if s.strip()]
        except ValueError:
            print(f"[!] Row {row_num + 2}: Invalid skill_ids '{raw_skills}' — skipping.")
            continue

        entries.append({
            "date": entry_date,
            "description": str(row["description"]).strip(),
            "hours": hours,
            "links": str(row["links"]).strip(),
            "learnings": str(row["learnings"]).strip(),
            "blockers": str(row["blockers"]).strip(),
            "skill_ids": skill_ids,
        })

    return entries


def submit_diary_entry(entry: dict) -> bool:
    """Submits a single diary entry dict to the API. Returns True on success."""

    payload = {
        "internship_id": TARGET_INTERNSHIP_ID,
        "date": entry["date"],
        "description": entry["description"],
        "hours": entry["hours"],
        "links": entry["links"],
        "learnings": entry["learnings"],
        "blockers": entry["blockers"],
        "skill_ids": entry["skill_ids"],
        "mood_slider": 5,
    }

    print(f"[*] Submitting {entry['date']} ({entry['hours']} hrs)...")
    try:
        response = requests.post(SUBMIT_API_URL, headers=HEADERS, json=payload)

        if response.status_code in [200, 201]:
            print(f"[+] Success for {entry['date']}!")
            print("    Response:", json.dumps(response.json(), indent=4))
            return True
        else:
            print(f"[-] Failed for {entry['date']} — HTTP {response.status_code}")
            print("    Response:", response.text)
            print("\n    Tip: Check Chrome DevTools Network tab to verify the exact payload format.")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[-] Request error for {entry['date']}: {e}")
        return False


if __name__ == "__main__":
    print("--- Internshipyet Excel Diary Filler ---\n")
    print(f"[*] Reading entries from: {EXCEL_FILE_PATH}")

    try:
        entries = load_excel_entries(EXCEL_FILE_PATH)
    except (FileNotFoundError, ValueError) as e:
        print(f"[-] {e}")
        raise SystemExit(1)

    if not entries:
        print("[-] No valid entries found in the Excel file. Aborting.")
        raise SystemExit(1)

    print(f"[*] Loaded {len(entries)} entries from Excel.")

    if not verify_token():
        print("[-] Aborting due to authentication error.")
        raise SystemExit(1)

    success_count = 0
    fail_count = 0

    for index, entry in enumerate(entries):
        print(f"\n{'─' * 48}")
        print(f"[*] Processing entry {index + 1}/{len(entries)}: {entry['date']}")

        ok = submit_diary_entry(entry)
        if ok:
            success_count += 1
        else:
            fail_count += 1

        if index < len(entries) - 1:
            print(f"[*] Waiting {DELAY_BETWEEN_APPLIES}s before next submission...")
            time.sleep(DELAY_BETWEEN_APPLIES)

    print(f"\n{'=' * 48}")
    print(f"[+] Done!  ✓ {success_count} succeeded   ✗ {fail_count} failed")
