#!/usr/bin/env python3
"""
embed_prep.py (NEW OpenAI API v1.x compatible)

Reads batch files from processed/embed_batches/
Generates embeddings using text-embedding-3-large
Writes output to processed/embeddings/
Tracks progress in processed/embeddings_manifest.json
"""

import json
import time
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Create OpenAI client using new SDK
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BATCH_DIR = Path("processed/embed_batches")
OUT_DIR = Path("processed/embeddings")
MANIFEST_FILE = Path("processed/embeddings_manifest.json")

MODEL_NAME = "text-embedding-3-large"
RATE_DELAY = 0.3   # delay between API calls

def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {"embedded": []}

def save_manifest(m):
    MANIFEST_FILE.write_text(
        json.dumps(m, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def embed_text(text):
    """Generate embeddings using the new OpenAI client."""
    for attempt in range(5):
        try:
            result = client.embeddings.create(
                model=MODEL_NAME,
                input=text
            )
            return result.data[0].embedding

        except Exception as e:
            print("API error, retrying:", e)
            time.sleep(1 + attempt)

    return None


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    batch_files = sorted(BATCH_DIR.glob("batch_*.json"))

    if not batch_files:
        print("No embedding batches found.")
        return

    for batch_path in batch_files:
        print("Processing batch:", batch_path)

        batch = json.loads(batch_path.read_text(encoding="utf-8"))
        out_batch = []

        for item in batch:
            chunk_id = item["chunk_id"]

            if chunk_id in manifest["embedded"]:
                continue

            emb = embed_text(item["chunk_text"])
            if emb is None:
                print("Failed to embed:", chunk_id)
                continue

            out_batch.append({
                "chunk_id": chunk_id,
                "embedding": emb,
                "source": item["source"],
                "raw_file": item["raw_file"],
                "chunk_index": item["chunk_index"],
                "title": item["title"],
                "url": item["url"],
                "chunk_text": item["chunk_text"]
            })

            manifest["embedded"].append(chunk_id)
            print("Embedded:", chunk_id)

            time.sleep(RATE_DELAY)

        out_file = OUT_DIR / ("emb_" + batch_path.name)
        out_file.write_text(
            json.dumps(out_batch, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        save_manifest(manifest)
        print("Wrote embeddings:", out_file)

    print("All batches processed.")
    print("Total embedded:", len(manifest["embedded"]))


if __name__ == "__main__":
    main()
