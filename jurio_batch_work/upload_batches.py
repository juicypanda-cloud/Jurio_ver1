#!/usr/bin/env python3
"""
upload_batches.py (FINAL FIXED VERSION)
- Loads .env correctly
- Uses REST API (no Supabase SDK)
- Works with Service Role Key
- Uploads batch_*.gz safely
"""

import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------
# Load .env from the correct absolute path
# ---------------------------------------------------------
load_dotenv(dotenv_path="/workspaces/Jurio_ver1/jurio_batch_work/.env")

# ---------------------------------------------------------
# Environment variables
# ---------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "chunks")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL missing from .env!")

if not SERVICE_KEY:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY missing from .env!")

UPLOAD_URL = f"{SUPABASE_URL}/storage/v1/object"


# ---------------------------------------------------------
# Check if remote exists using HEAD
# ---------------------------------------------------------
def remote_exists(name: str) -> bool:
    url = f"{UPLOAD_URL}/{BUCKET}/{name}"
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
    }
    try:
        res = requests.head(url, headers=headers)
        return res.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------
# Upload a single file with retry
# ---------------------------------------------------------
def upload_file(path: Path):
    name = path.name

    if remote_exists(name):
        print(f"[SKIP] {name} already exists")
        return True

    url = f"{UPLOAD_URL}/{BUCKET}/{name}"
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/octet-stream",
    }
    data = path.read_bytes()

    for attempt in range(1, 6):
        try:
            res = requests.post(url, headers=headers, data=data)

            if res.status_code in (200, 201):
                print(f"[OK] Uploaded {name}")
                return True

            print(f"[WARN] {name} attempt {attempt}: {res.status_code} {res.text}")
            time.sleep(attempt * 1.2)

        except Exception as e:
            print(f"[ERR] {name} attempt {attempt}: {e}")
            time.sleep(attempt * 1.2)

    print(f"[FAILED] Could not upload {name}")
    return False


# ---------------------------------------------------------
# Main upload loop
# ---------------------------------------------------------
def main():
    batch_dir = Path("batches")
    files = sorted(batch_dir.glob("batch_*.gz"))

    if not files:
        print("No batch_*.gz files found.")
        return

    success_count = 0

    for f in files:
        if upload_file(f):
            success_count += 1

    print(f"\nUploaded {success_count}/{len(files)} batch files")


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
