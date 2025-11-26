# shuukh_spider.py
# Full-site spider for shuukh.mn — Playwright (sync)
# Saves all detected court decisions to ../data_store/shuukh_full/
# Usage: python scrapers/shuukh_spider.py

import sys
import os
import time
from pathlib import Path
from collections import deque

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.save_json import save_json

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE = "https://shuukh.mn"
START = "https://shuukh.mn"
OUT_DIR = Path("../data_store/shuukh_full")

# Patterns that indicate case/decision pages
DOC_PATTERNS = [
    "/case",
    "/decision",
    "/court",
    "/shuukh",
    "/detail",
    "/judgement",
    "/resolve",
    "/order"
]

MAX_PAGES = 8000         # safety cap for maximum crawl pages
PAGE_TIMEOUT_MS = 45000  # max timeout per page
WAIT_AFTER_LOAD = 1200   # ms delay after load
CRAWL_DELAY = 0.5        # polite delay between pages


def looks_like_doc(url: str) -> bool:
    url = url.lower()
    return any(p in url for p in DOC_PATTERNS)


def normalize(href: str) -> str:
    """Convert relative/absolute URLs to full URLs."""
    if href.startswith("http"):
        return href.rstrip("/")
    if href.startswith("//"):
        return "https:" + href.rstrip("/")
    return BASE + href.rstrip("/")


def extract_text(page):
    """Extract text from a decision/case page."""
    selectors = [
        ".decision-text",
        ".case-body",
        ".content",
        "article",
        "#content",
        "body",
    ]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if len(text) > 150:
                    return text
        except:
            pass
    return ""


def extract_title(page):
    try:
        t = page.query_selector("h1")
        if t:
            return t.inner_text().strip()
    except:
        pass
    return "Untitled"


def collect_links(page):
    """Get internal links from the page."""
    links = []
    for a in page.query_selector_all("a"):
        try:
            href = a.get_attribute("href")
            if not href:
                continue
            url = normalize(href)
            if url.startswith(BASE):
                links.append(url)
        except:
            continue
    return links


def spider():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    visited = set()
    docs = set()

    queue = deque([START])
    count = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        # Spoof realistic browser headers
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/119.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

        while queue and len(visited) < MAX_PAGES:
            url = queue.popleft()

            if url in visited:
                continue

            visited.add(url)
            count += 1
            print(f"[{count}] Visiting:", url)

            # try to load page
            try:
                page.goto(url, timeout=PAGE_TIMEOUT_MS)
                page.wait_for_timeout(WAIT_AFTER_LOAD)
            except PlaywrightTimeout:
                print("   -- timeout")
                continue
            except:
                print("   -- navigation error")
                continue

            # collect new internal links
            new_links = collect_links(page)
            for link in new_links:
                if link not in visited:
                    queue.append(link)

            # if URL looks like a case/decision, extract it
            if looks_like_doc(url) and url not in docs:
                title = extract_title(page)
                text = extract_text(page)

                if len(text) > 200:
                    fname = f"case_{len(docs)}.json"
                    save_json({"url": url, "title": title, "text": text},
                              OUT_DIR, fname)
                    docs.add(url)
                    print(f"   ++ saved {fname}, text_length={len(text)}")

            time.sleep(CRAWL_DELAY)

        browser.close()

    print("\n=== CRAWL COMPLETE ===")
    print("Total pages visited:", len(visited))
    print("Total court docs saved:", len(docs))


if __name__ == "__main__":
    spider()
