#!/usr/bin/env python3
"""
embed_fast.py  (10x faster embedding)
- Uses batch embedding (up to 100 chunks per request)
- Uses async concurrency (5 parallel workers)
- Writes output in the same format as embed_prep.py
"""

import json
import os
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "text-embedding-3-large"

BATCH_DIR = Path("processed/embed_batches")
OUT_DIR = Path("processed/embeddings")
MANIFEST_FILE = Path("processed/embeddings_manifest.json")

# Concurrency settings
MAX_PARALLEL = 5           # number of parallel tasks
MAX_EMBED_BATCH_SIZE = 100 # embeddings per API call


def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {"embedded": []}


def save_manifest(m):
    MANIFEST_FILE.write_text(
        json.dumps(m, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


async def embed_batch(session, chunk_batch):
    """Send a batch of up to 100 texts to OpenAI embeddings."""
    payload = {
        "model": MODEL,
        "input": [c["chunk_text"] for c in chunk_batch]
    }

    for attempt in range(5):
        try:
            async with session.post(
                "https://api.openai.com/v1/embeddings",
                json=payload,
                headers={"Authorization": f"Bearer {API_KEY}"}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data
                else:
                    print("API error:", resp.status, await resp.text())
        except Exception as e:
            print("Retrying:", e)

        await asyncio.sleep(1 + attempt)

    return None


async def process_single_batch(session, batch_path, manifest):
    """Process one batch_XX.json file quickly."""
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    out_batch = []

    # Filter out already-embedded
    remaining = [item for item in batch if item["chunk_id"] not in manifest["embedded"]]

    if not remaining:
        print("Already complete:", batch_path)
        return

    print(f"Processing {batch_path.name}, {len(remaining)} chunks left")

    # Split into sub-batches of size 100
    sub_batches = [
        remaining[i:i + MAX_EMBED_BATCH_SIZE]
        for i in range(0, len(remaining), MAX_EMBED_BATCH_SIZE)
    ]

    for sub in sub_batches:
        result = await embed_batch(session, sub)
        if not result:
            print("Failed sub-batch:", sub[0]["chunk_id"])
            continue

        embeddings = result["data"]

        for idx, item in enumerate(sub):
            emb = embeddings[idx]["embedding"]
            out_batch.append({
                "chunk_id": item["chunk_id"],
                "embedding": emb,
                "source": item["source"],
                "raw_file": item["raw_file"],
                "chunk_index": item["chunk_index"],
                "title": item["title"],
                "url": item["url"],
                "chunk_text": item["chunk_text"]
            })

            manifest["embedded"].append(item["chunk_id"])

        print(f"Embedded {len(sub)} chunks")

    # Write output
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / ("emb_" + batch_path.name)
    out_file.write_text(json.dumps(out_batch, ensure_ascii=False, indent=2), encoding="utf-8")
    save_manifest(manifest)

    print("Wrote:", out_file)


async def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    batch_files = sorted(BATCH_DIR.glob("batch_*.json"))

    async with aiohttp.ClientSession() as session:
        tasks = []
        sem = asyncio.Semaphore(MAX_PARALLEL)

        async def sem_task(path):
            async with sem:
                await process_single_batch(session, path, manifest)

        for batch_path in batch_files:
            tasks.append(asyncio.create_task(sem_task(batch_path)))

        await asyncio.gather(*tasks)

    print("All batches processed fast.")
    print("Total embedded:", len(manifest["embedded"]))


if __name__ == "__main__":
    asyncio.run(main())
