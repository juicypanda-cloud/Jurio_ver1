#!/usr/bin/env python3
"""
process_documents.py

- Scans raw scraped folders:
    data_store/legalinfo_full/
    data_store/shuukh_full/
- For each raw JSON file not yet processed, extract text, chunk it, and save:
    processed/chunks/{source}/{raw_filename}_chunks.json
- Maintain manifest: processed/processed_manifest.json
- Prepare embed queue: processed/embed_queue.json
"""

import json
from pathlib import Path
from utils.save_json import save_json
from utils.chunk_text import chunk_text, clean_text
import time

RAW_DIRS = {
    "legalinfo": Path("data_store/legalinfo_full"),
    "shuukh": Path("data_store/shuukh_full")
}

PROCESSED_BASE = Path("processed")
CHUNKS_DIR = PROCESSED_BASE / "chunks"
MANIFEST_FILE = PROCESSED_BASE / "processed_manifest.json"
EMBED_QUEUE = PROCESSED_BASE / "embed_queue.json"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 150

def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    else:
        return {"processed": {}}

def save_manifest(manifest):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

def list_raw_files():
    files = []
    for source, p in RAW_DIRS.items():
        if not p.exists():
            continue
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix.lower() == ".json":
                files.append((source, f))
    return files

def extract_text_from_raw(raw_json):
    # raw_json is a dict loaded from the scrapers: it should contain 'text' or 'content'
    text = ""
    if isinstance(raw_json, dict):
        # common keys we might have used earlier
        for key in ("text", "content", "extracted_text"):
            if key in raw_json and raw_json[key]:
                text = raw_json[key]
                break
        # Some scrapers used nested fields or 'body'
        if not text:
            for k in raw_json.keys():
                if isinstance(raw_json[k], str) and len(raw_json[k])>200:
                    text = raw_json[k]
                    break
    return text or ""

def process_one(source, raw_path, manifest, embed_items):
    rawname = raw_path.name
    already = manifest["processed"].get(source, [])
    if rawname in already:
        return False

    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to load {raw_path}: {e}")
        return False

    text = extract_text_from_raw(raw)
    text = clean_text(text)
    if not text or len(text) < 200:
        print(f"Skipping {rawname} - no useful text or too short ({len(text)})")
        # still mark as processed to avoid retry loops
        manifest["processed"].setdefault(source, []).append(rawname)
        return False

    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    CHUNKS_DIR.joinpath(source).mkdir(parents=True, exist_ok=True)
    out_name = CHUNKS_DIR.joinpath(source, rawname.replace(".json", "") + "_chunks.json")
    save_json({"source": source, "raw_file": rawname, "chunks": chunks, "metadata": raw.get("metadata", {})}, out_name.name and out_name.parent, out_name.name)
    # note: save_json handles path creation

    # add entries to embed queue metadata
    for i, chunk in enumerate(chunks):
        embed_items.append({
            "source": source,
            "raw_file": rawname,
            "chunk_index": i,
            "chunk_text": chunk,
            "chunk_id": f"{rawname}::chunk_{i}",
            "title": raw.get("title") or raw.get("url") or rawname,
            "url": raw.get("url") or ""
        })

    # update manifest
    manifest["processed"].setdefault(source, []).append(rawname)
    manifest["last_processed"] = time.time()
    print(f"Processed {rawname}: {len(chunks)} chunks")
    return True

def main():
    manifest = load_manifest()
    raw_files = list_raw_files()
    embed_items = []

    processed_count = 0
    for source, raw_path in raw_files:
        processed = process_one(source, raw_path, manifest, embed_items)
        if processed:
            processed_count += 1

    # save manifest and embed queue
    save_manifest(manifest)
    # write embed queue (append to existing if present)
    existing_queue = []
    if EMBED_QUEUE.exists():
        try:
            existing_queue = json.loads(EMBED_QUEUE.read_text(encoding="utf-8"))
        except:
            existing_queue = []
    # Avoid duplicate chunk_id entries (simple de-dupe)
    existing_ids = { item.get("chunk_id") for item in existing_queue }
    new_items = [it for it in embed_items if it["chunk_id"] not in existing_ids]
    final_queue = existing_queue + new_items
    EMBED_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    EMBED_QUEUE.write_text(json.dumps(final_queue, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Done. Documents processed:", processed_count)
    print("Embed queue length:", len(final_queue))

if __name__ == "__main__":
    main()
