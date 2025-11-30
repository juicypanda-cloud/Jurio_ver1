#!/usr/bin/env python3
"""
create_batches.py

Reads embed_queue.json and splits it into batches for embedding.
Creates:
    processed/embed_batches/batch_0.json
    processed/embed_batches/batch_1.json
    ...
"""

import json
from pathlib import Path

PROCESSED_DIR = Path("processed")
QUEUE_FILE = PROCESSED_DIR / "embed_queue.json"
BATCH_DIR = PROCESSED_DIR / "embed_batches"

BATCH_SIZE = 300  # number of chunks per batch


def main():
    if not QUEUE_FILE.exists():
        print("No embed_queue.json found. Run process_documents.py first.")
        return

    # Ensure output directory exists
    BATCH_DIR.mkdir(parents=True, exist_ok=True)

    queue = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    print(f"Total queue items: {len(queue)}")

    if not queue:
        print("Queue is empty, nothing to batch.")
        return

    # Create batches
    batches = [
        queue[i : i + BATCH_SIZE]
        for i in range(0, len(queue), BATCH_SIZE)
    ]

    # Save batch files
    for idx, batch in enumerate(batches):
        batch_file = BATCH_DIR / f"batch_{idx}.json"
        batch_file.write_text(
            json.dumps(batch, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Created {batch_file} with {len(batch)} items")

    print(f"\nTotal batches created: {len(batches)}")


if __name__ == "__main__":
    main()
