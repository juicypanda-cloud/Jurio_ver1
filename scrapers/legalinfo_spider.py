# legalinfo_spider.py
# Full-site spider for legalinfo.mn — uses Playwright (sync)
# Saves all detected legal docs to ../data_store/legalinfo_full/
# Usage: python scrapers/legalinfo_spider.py

import sys
import os
import time
from collections import deque
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.save_json import save_json

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

BASE = "https://legalinfo.mn"
START = "https://legalinfo.mn/mn"
OUT_DIR = Path("../data_store/legalinfo_full")

# patterns to consider legal documents (expand if needed)
DOC_KEYWORDS = [
    "/mn/law/", "/law/",
    "/resolution/", "/decree/",
    "/policy/", "/normative/",
    "/bylaw/", "/act/",
    "/mn/detail", "/mn/decision", "/mn/resolution",
    "/mn/bylaw", "/mn/normative", "/mn/policy",
    "/mn/act", "/mn/doc", "/mn/article"
]

# runtime controls
MAX_PAGES = 5000          # absolute safety cap to avoid infinite crawl
MAX_VISIT_PER_DOMAIN = 10000
PAGE_TIMEOUT_MS = 45000   # 45s per page
WAIT_AFTER_NAV = 1.0      # seconds
SLEEP_BETWEEN_REQUESTS = 0.6  # polite crawling

def looks_like_doc(url: str) -> bool:
    u = url.lower()
    return any(k in u for k in DOC_KEYWORDS)

def normalize_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href.split("#")[0].rstrip("/")
    if href.startswith("//"):
        return "https:" + href.split("#")[0].rstrip("/")
    # relative
    return (BASE + href).split("#")[0].rstrip("/")

def extract_links_from_page(page):
    anchors = page.query_selector_all("a")
    out = []
    for a in anchors:
        try:
            href = a.get_attribute("href")
        except Exception:
            href = None
        if not href:
            continue
        try:
            full = normalize_url(href)
            # only internal links to legalinfo.mn
            if full.startswith(BASE):
                out.append(full)
        except Exception:
            continue
    return out

def extract_title_and_text(page):
    # try several selectors for title and main content
    title = ""
    text = ""
    try:
        t = page.query_selector("h1")
        if t:
            title = t.inner_text().strip()
    except Exception:
        title = ""

    # try a list of content selectors
    selectors = ["#content", ".law-text", ".article-body", "article", ".content", ".decision-text"]
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if len(text) > 100:
                    break
        except Exception:
            continue

    # fallback: whole body
    if not text:
        try:
            body = page.query_selector("body")
            if body:
                text = body.inner_text().strip()
        except Exception:
            text = ""

    return title, text

def spider(run_headless=True, max_pages=MAX_PAGES):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    visited = set()
    docs = set()
    q = deque([START])
    pages_crawled = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=run_headless)
        page = browser.new_page()
        # set real browser-like headers
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })

        while q and pages_crawled < max_pages:
            url = q.popleft()
            if url in visited:
                continue
            visited.add(url)
            pages_crawled += 1

            print(f"[{pages_crawled}] Visiting: {url}")
            try:
                page.goto(url, timeout=PAGE_TIMEOUT_MS)
                # allow JS to load
                page.wait_for_timeout(int(WAIT_AFTER_NAV * 1000))
                # try to scroll to trigger lazy content
                page.evaluate("window.scrollTo(0, 0)")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(600)
            except PlaywrightTimeout:
                print("  -- timeout loading:", url)
            except Exception as e:
                print("  -- error loading:", e)

            # extract links
            try:
                links = extract_links_from_page(page)
            except Exception as e:
                links = []
                print("  -- link extraction failed:", e)

            # enqueue new internal links
            for link in links:
                if link not in visited and len(visited) < MAX_VISIT_PER_DOMAIN:
                    q.append(link)

            # detect doc-like pages and save
            if looks_like_doc(url) or any(looks_like_doc(l) for l in links):
                # only save each document URL once
                if url not in docs:
                    title, text = extract_title_and_text(page)
                    # minimal filter to not save tiny pages
                    if len(text) > 200:
                        fname = f"doc_{len(docs)}.json"
                        save_json({"url": url, "title": title, "text": text}, OUT_DIR, fname)
                        docs.add(url)
                        print(f"  ++ saved: {fname} (len text={len(text)})")
                    else:
                        # sometimes doc link redirects to index; try to search child links for doc pages
                        for l in links:
                            if looks_like_doc(l) and l not in docs:
                                try:
                                    page.goto(l, timeout=PAGE_TIMEOUT_MS)
                                    page.wait_for_timeout(int(WAIT_AFTER_NAV * 1000))
                                    t2, txt2 = extract_title_and_text(page)
                                    if len(txt2) > 200:
                                        fname = f"doc_{len(docs)}.json"
                                        save_json({"url": l, "title": t2, "text": txt2}, OUT_DIR, fname)
                                        docs.add(l)
                                        print(f"  ++ saved (child): {fname} (len={len(txt2)})")
                                        break
                                except Exception:
                                    continue

            # polite sleep
            time.sleep(SLEEP_BETWEEN_REQUESTS)

        browser.close()

    print("\nCrawl finished.")
    print("Visited pages:", len(visited))
    print("Documents saved:", len(docs))

if __name__ == "__main__":
    spider(run_headless=True)
