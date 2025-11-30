#!/usr/bin/env python3
"""
batch_builder.py (string-safe version, fully fixed)
- Works with non-numeric chunk IDs (e.g., "doc_0.json::chunk_0")
- Reads chunks from chunks.jsonl
- Creates batch_*.gz files
- Creates metadata.json
"""

import os
import json
import gzip
import argparse
from pathlib import Path

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1000"))
SEPARATOR = "\n\n"

def read_chunks_from_jsonl(path="chunks.jsonl"):
    p = Path(path)
    if not p.exists():
        return None
    chunks = []
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj["id"]            # STRING ID
            text = obj["text"]
            chunks.append({"id": cid, "text": text})
    return chunks

def main(force=False, outdir="batches"):
    os.makedirs(outdir, exist_ok=True)

    chunks = read_chunks_from_jsonl("chunks.jsonl")
    if not chunks:
        print("❌ No chunks.jsonl found or file is empty.")
        return

    print(f"Loaded {len(chunks)} chunks.")

    # Sort by string ID
    chunks = sorted(chunks, key=lambda x: str(x["id"]))

    metadata = {}
    total = len(chunks)

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i+BATCH_SIZE]
        batch_id = f"batch_{i//BATCH_SIZE}"
        out_path = Path(outdir) / f"{batch_id}.gz"

        if out_path.exists() and not force:
            print(f"{out_path} exists – skipping (use --force to overwrite)")
            continue

        # extract texts only
        texts = [entry["text"] for entry in batch]

        # join with separator
        joined_text = SEPARATOR.join(texts)
        joined_bytes = joined_text.encode("utf-8")

        # compute offsets
        offsets = []
        pos = 0
        sep_bytes = SEPARATOR.encode("utf-8")

        for entry in batch:
            text = entry["text"]
            text_bytes = text.encode("utf-8")

            start = pos
            end = pos + len(text_bytes) - 1

            offsets.append({
                "chunk_id": entry["id"],   # ✔ use entry here
                "start": start,
                "end": end
            })

            # move forward by this text + separator
            pos = end + 1 + len(sep_bytes)

        # write gzip
        with gzip.open(out_path, "wb") as gz:
            gz.write(joined_bytes)

        metadata[batch_id] = {
            "num_chunks": len(batch),
            "chunk_ids": [entry["id"] for entry in batch],
            "chunk_offsets": offsets
        }

        print(f"✔ Created {out_path} ({len(batch)} chunks)")

    # save metadata.json
    meta_path = Path(outdir) / "metadata.json"
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print("\n=== DONE ===")
    print("Saved metadata →", meta_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--outdir", default="batches")
    args = parser.parse_args()

    main(force=args.force, outdir=args.outdir)
