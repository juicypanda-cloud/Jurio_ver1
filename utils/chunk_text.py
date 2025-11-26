# chunk_text.py
import re

def clean_text(text: str) -> str:
    """Basic cleaning: normalize whitespace and newlines."""
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)          # collapse multiple newlines
    text = re.sub(r"[ \t]+", " ", text)       # collapse spaces/tabs
    text = re.sub(r" *\n *", "\n", text)      # trim spaces around newlines
    return text.strip()

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 150):
    """
    Split text into overlapping character-based chunks.
    Returns list of chunk strings.
    """
    text = clean_text(text)
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)
    step = max(1, chunk_size - overlap)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if len(chunk) > 0:
            chunks.append(chunk)
        if end == n:
            break
        start += step

    return chunks
