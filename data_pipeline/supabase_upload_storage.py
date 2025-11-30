#!/usr/bin/env python3
import os, json, gzip, time
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EMB_DIR = Path("processed/embeddings")
BUCKET = "chunks"
MANIFEST = Path("processed/upload_manifest.json")

# Load manifest
if MANIFEST.exists():
    manifest = json.loads(MANIFEST.read_text())
else:
    manifest = {"uploaded": []}
uploaded = set(manifest["uploaded"])


def upload_with_retry(bucket, path, data, max_retries=5):
    for attempt in range(max_retries):
        try:
            supabase.storage.from_(bucket).upload(path, data)
            return True
        except Exception as e:
            msg = str(e)
            if "exists" in msg or "Duplicate" in msg:
                return True  # already there
            print(f"Retry {attempt+1}/{max_retries} for {path}: {msg}")
            time.sleep(1.0 + attempt * 0.5)
    return False


print("\n=== Starting stable upload ===\n")
files = sorted(EMB_DIR.glob("emb_batch_*.json"))

for emb_file in files:
    print(f"\n=== Processing {emb_file} ===")

    items = json.loads(emb_file.read_text())
    for item in items:

        cid = item["chunk_id"]
        if cid in uploaded:
            continue

        t = item["chunk_text"]
        gz_bytes = gzip.compress(t.encode("utf-8"))
        path = f"{cid}.txt.gz"

        ok = upload_with_retry(BUCKET, path, gz_bytes)
        if ok:
            uploaded.add(cid)
            print("✔️", cid)
        else:
            print("❌ Failed:", cid)

        # Save manifest every 50 chunks
        if len(uploaded) % 50 == 0:
            MANIFEST.write_text(json.dumps({"uploaded": list(uploaded)}, indent=2))

# Final save
MANIFEST.write_text(json.dumps({"uploaded": list(uploaded)}, indent=2))
print("\n=== Upload finished ===")
print("Total uploaded:", len(uploaded))
