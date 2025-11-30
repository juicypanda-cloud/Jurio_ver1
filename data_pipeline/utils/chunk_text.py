import re

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()

def chunk_text(text: str, chunk_size: int = 1500, overlap: int = 200):
    text = clean_text(text)
    if not text:
        return []

    chunks = []
    n = len(text)
    step = max(1, chunk_size - overlap)
    start = 0

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start += step

    return chunks
