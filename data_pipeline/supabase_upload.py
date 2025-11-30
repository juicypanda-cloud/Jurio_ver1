#!/usr/bin/env python3
"""
supabase_upload.py

Uploads ALL embedded chunks into Supabase `documents` table.
This version removes skip logic to ensure full upload of all batches.
"""

import json
import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

EMB_DIR = Path("processed/embeddings")
UPLOAD_MANIFEST = Path("processed/upload_manifest.json")

def main():
    emb_files = sorted(EMB_DIR.glob("emb_batch_*.json"))
    if not emb_files:
        print("No embedding batch files found.")
        return

    total_inserted = 0

    for emb_path in emb_files:
        print("Uploading:", emb_path)
        items = json.loads(emb_path.read_text(encoding="utf-8"))

        rows_to_insert = []
        for it in items:
            rows_to_insert.append({
                "doc_type": it["source"],
                "title": it["title"],
                "identifier": it["chunk_id"],   # stable identifier
                "chunk_id": it["chunk_id"],
                "source": it["source"],
                "origin_url": it["url"],
                "content": it["chunk_text"],
                "embedding": it["embedding"],
                "metadata": {
                    "raw_file": it["raw_file"],
                    "chunk_index": it["chunk_index"],
                }
            })

        if rows_to_insert:
            print(f"Inserting {len(rows_to_insert)} rows...")

            chunk_size = 50
            for i in range(0, len(rows_to_insert), chunk_size):
                chunk = rows_to_insert[i:i + chunk_size]
                supabase.table("documents").insert(chunk).execute()
                total_inserted += len(chunk)

    print("\nUpload complete.")
    print("Total inserted:", total_inserted)


if __name__ == "__main__":
    main()
