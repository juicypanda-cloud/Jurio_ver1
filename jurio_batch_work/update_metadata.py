#!/usr/bin/env python3
"""
update_metadata.py (string-safe version)
- Loads batches/metadata.json
- Inserts/Upserts:
    chunk_id (string)
    batch_id
    start
    end
- No int() conversion (supports IDs like "case_0.json::chunk_0")
"""

import os
import json
import time
from pathlib import Path

try:
    from supabase import create_client
except Exception as e:
    print("Please install supabase: pip install supabase")
    raise

# Load dotenv if available
from dotenv import load_dotenv
load_dotenv(dotenv_path="/workspaces/Jurio_ver1/jurio_batch_work/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
TABLE = os.getenv("SUPABASE_TABLE", "documents")

if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL")
if not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_DB = int(os.getenv("DB_BATCH", "50"))
SLEEP_BETWEEN_BATCHES = float(os.getenv("DB_SLEEP", "0.2"))


def load_metadata(path="batches/metadata.json"):
    p = Path(path)
    if not p.exists():
        raise RuntimeError("metadata.json not found")
    return json.loads(p.read_text(encoding="utf-8"))


def chunk_rows_from_metadata(meta):
    """
    Yield rows:
    {
       "chunk_id": <string>,
       "batch_id": <string>,
       "start": <int>,
       "end": <int>
    }
    """
    for batch_id, info in meta.items():
        offsets = info["chunk_offsets"]
        for off in offsets:
            yield {
                "chunk_id": off["chunk_id"],      # string ID
                "batch_id": batch_id,
                "start": int(off["start"]),
                "end": int(off["end"]),
            }


def upsert_rows(rows):
    res = client.table(TABLE).upsert(rows).execute()

    if isinstance(res, dict) and res.get("error"):
        print("DB error:", res["error"])
        return False

    # old client: (data, error)
    if isinstance(res, tuple) and res[1] is not None:
        print("DB error:", res[1])
        return False

    return True


def main():
    meta = load_metadata()
    gen = chunk_rows_from_metadata(meta)

    buffer = []
    count = 0

    for row in gen:
        buffer.append(row)

        if len(buffer) >= BATCH_DB:
            ok = upsert_rows(buffer)
            if not ok:
                print("Retry after error...")
                time.sleep(1)
                ok = upsert_rows(buffer)
                if not ok:
                    raise RuntimeError("Failed DB insert even after retry")

            count += len(buffer)
            print(f"Upserted {count} rows")
            buffer = []
            time.sleep(SLEEP_BETWEEN_BATCHES)

    if buffer:
        upsert_rows(buffer)
        count += len(buffer)
        print(f"Final upsert: {len(buffer)} rows")
        print(f"Total rows: {count}")


if __name__ == "__main__":
    main()
