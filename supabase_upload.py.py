#!/usr/bin/env python3
"""
supabase_upload.py

Uploads embedded chunks into Supabase `documents` table.
Only uploads items not yet inserted (uses upload_manifest.json).
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

def load_manifest():
    if UPLOAD_MANIFEST.exists():
        return json.loads(UPLOAD_MANIFEST.read_text(encoding="utf-8"))
    return {"uploaded": []}

def save_manifest(m):
    UPLOAD_MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    manifest = load_manifest()
    uploaded_ids = set(manifest["uploaded"])

    emb_files = sorted(EMB_DIR.glob("emb_batch_*.json"))
    if not emb_files:
        print("No embedding files found.")
        return

    for emb_path in emb_files:
        print("Uploading:", emb_path)
        items = json.loads(emb_path.read_text(encoding="utf-8"))

        rows_to_insert = []
        for it in items:
            cid = it["chunk_id"]
            if cid in uploaded_ids:
                continue

            rows_to_insert.append({
                "doc_type": it["source"],
                "title": it["title"],
                "identifier": it["chunk_id"],
                "source": it["source"],
                "origin_url": it["url"],
                "content": it["chunk_text"],
                "embedding": it["embedding"],
                "metadata": {
                    "raw_file": it["raw_file"],
                    "chunk_index": it["chunk_index"],
                }
            })

            manifest["uploaded"].append(cid)

        if rows_to_insert:
            print("Inserting", len(rows_to_insert), "rows into Supabase...")
            supabase.table("documents").insert(rows_to_insert).execute()
            save_manifest(manifest)
        else:
            print("No new rows to insert in this file.")

    print("Upload complete.")
    print("Total uploaded:", len(manifest["uploaded"]))

if __name__ == "__main__":
    main()
