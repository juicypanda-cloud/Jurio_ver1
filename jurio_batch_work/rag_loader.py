#!/usr/bin/env python3
"""
rag_loader.py (string-safe version)
Loads text chunks from batch_<id>.gz files stored in Supabase Storage.

Steps:
1. Query "documents" table for the given chunk_id (string).
2. Get batch_id, start, end byte offsets.
3. Download the batch file if missing.
4. Decompress it.
5. Slice by byte offset.
6. Return clean UTF-8 text.
"""

import os
import gzip
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

# Load correct env
load_dotenv("/workspaces/Jurio_ver1/jurio_batch_work/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET = os.getenv("SUPABASE_BUCKET", "chunks")

if not SUPABASE_URL:
    raise RuntimeError("Missing SUPABASE_URL")
if not SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

client = create_client(SUPABASE_URL, SERVICE_KEY)

CACHE_DIR = Path("/tmp/jurio_batch_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_mapping_for_chunk(chunk_id: str):
    """Return (batch_id, start, end) for a string chunk ID."""

    # STRING chunk_id, so no int() conversion
    q = (
        client.table("documents")
        .select("batch_id, start, end")
        .eq("chunk_id", chunk_id)
        .limit(1)
        .execute()
    )

    if isinstance(q, dict):
        data = q.get("data", [])
    else:
        data = q.data

    if not data:
        raise KeyError(f"No mapping found for chunk_id={chunk_id}")

    row = data[0]
    return row["batch_id"], int(row["start"]), int(row["end"])


def download_batch_if_needed(batch_id: str) -> Path:
    """Download batch file if not cached."""
    local = CACHE_DIR / f"{batch_id}.gz"
    if local.exists():
        return local

    url_path = f"{batch_id}.gz"
    res = client.storage.from_(BUCKET).download(url_path)

    # handle tuple (data, error)
    if isinstance(res, tuple):
        data = res[0]
    elif isinstance(res, dict):
        data = res.get("data")
    else:
        data = res

    if not isinstance(data, (bytes, bytearray)):
        raise RuntimeError(f"Failed to download {url_path}: {res}")

    with open(local, "wb") as f:
        f.write(data)

    return local


def get_chunk_text(chunk_id: str) -> str:
    """Main function: return the chunk text for any string chunk_id."""

    batch_id, start, end = get_mapping_for_chunk(chunk_id)

    local_gz = download_batch_if_needed(batch_id)

    # read batch file
    with gzip.open(local_gz, "rb") as gz:
        data = gz.read()  # decompressed bytes

    part = data[start : end + 1]

    try:
        return part.decode("utf-8")
    except:
        return part.decode("utf-8", errors="replace")


# Self-test
if __name__ == "__main__":
    test_id = "case_0.json::chunk_0"
    print("Testing:", test_id)
    print(get_chunk_text(test_id)[:500])
