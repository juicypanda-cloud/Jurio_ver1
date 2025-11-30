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

# =====================================================================
# FIX: Add project root to Python path so imports ALWAYS work
# =====================================================================

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent  # /workspaces/Jurio_ver1/
sys.path.append(str(ROOT_DIR))

# =====================================================================
# IMPORTS
# =====================================================================

import json
import time
from data_pipeline.utils.save_json import save_json
from data_pipeline.utils.chunk_text import chunk_text, clean_text

# =====================================================================
# PATH SETTINGS
# =====================================================================

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

# =====================================================================
# MANIFEST HANDLING
# =====================================================================

def load_manifest():
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {"processed": {}}

def save_manifest(manifest):
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

# =====================================================================
# RAW FILE DISCOVERY
# =====================================================================

def list_raw_files():
    files = []
    for source, p in RAW_DIRS.items():
        if not p.exists():
            continue
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix.lower() == ".json":
                files.append((source, f))
    return files

# =====================================================================
# TEXT EXTRACTION
# =====================================================================

def extract_text_from_raw(raw_json):
    """
    Extract text from raw JSON using common keys or long strings.
    """
    text = ""

    if isinstance(raw_json, dict):
        # Try known keys
        for key in ("text", "content", "extracted_text", "body"):
            if key in raw_json and raw_json[key]:
                text = raw_json[key]
                break

        # Fallback: any long string field
        if not text:
            for k, v in raw_json.items():
                if isinstance(v, str) and len(v) > 200:
                    text = v
                    break

    return text or ""

# =====================================================================
# PROCESS ONE RAW DOCUMENT
# =====================================================================

def process_one(source, raw_path, manifest, embed_items):
    rawname = raw_path.name

    # Skip if already processed
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
        manifest["processed"].setdefault(source, []).append(rawname)
        return False

    # Chunk the file
    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

    # Output chunks
    CHUNKS_DIR.joinpath(source).mkdir(parents=True, exist_ok=True)
    out_path = CHUNKS_DIR.joinpath(
        source, rawname.replace(".json", "") + "_chunks.json"
    )

    save_json(
        {
            "source": source,
            "raw_file": rawname,
            "chunks": chunks,
            "metadata": raw.get("metadata", {})
        },
        out_path.parent,
        out_path.name
    )

    # Prepare embed queue items
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

    manifest["processed"].setdefault(source, []).append(rawname)
    manifest["last_processed"] = time.time()

    print(f"Processed {rawname}: {len(chunks)} chunks")
    return True

# =====================================================================
# MAIN PIPELINE LOGIC
# =====================================================================

def main():
    manifest = load_manifest()
    raw_files = list_raw_files()
    embed_items = []

    processed_count = 0

    for source, raw_path in raw_files:
        if process_one(source, raw_path, manifest, embed_items):
            processed_count += 1

    save_manifest(manifest)

    # Merge embed queue
    existing_queue = []
    if EMBED_QUEUE.exists():
        try:
            existing_queue = json.loads(EMBED_QUEUE.read_text(encoding="utf-8"))
        except:
            existing_queue = []

    existing_ids = {item.get("chunk_id") for item in existing_queue}
    new_items = [it for it in embed_items if it["chunk_id"] not in existing_ids]
    final_queue = existing_queue + new_items

    EMBED_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    EMBED_QUEUE.write_text(
        json.dumps(final_queue, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("\nDone.")
    print("Documents processed:", processed_count)
    print("Embed queue length:", len(final_queue))

if __name__ == "__main__":
    main()
