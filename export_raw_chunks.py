#!/usr/bin/env python3
"""
export_raw_chunks.py
Extracts ALL chunk_id + chunk_text pairs from:

    processed/embeddings/emb_batch_*.json

and writes them into:

    chunks.jsonl

One line per chunk:
{
    "id": <chunk_id>,
    "text": "<chunk_text>"
}

This file becomes the source for batch_builder.py.
"""

import json
from pathlib import Path

EMB_DIR = Path("processed/embeddings")
OUT = Path("chunks.jsonl")

def main():
    if not EMB_DIR.exists():
        raise RuntimeError(f"{EMB_DIR} does not exist. You must run this inside project root.")

    files = sorted(EMB_DIR.glob("emb_batch_*.json"))
    if not files:
        raise RuntimeError(f"No emb_batch_*.json files found in {EMB_DIR}")

    print(f"Found {len(files)} embedding batch files.")
    count = 0

    with OUT.open("w", encoding="utf-8") as out:
        for f in files:
            print(f"Reading {f}...")
            items = json.loads(f.read_text())
            for it in items:
                cid = it["chunk_id"]
                text = it["chunk_text"]

                obj = {"id": cid, "text": text}
                out.write(json.dumps(obj, ensure_ascii=False) + "\n")

                count += 1

    print("\n=== DONE ===")
    print(f"Wrote {count} chunks to {OUT}")

if __name__ == "__main__":
    main()
