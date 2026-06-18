"""
圓夢繪本 metadata crawler（All Rights Reserved — 僅收集書目資訊）。

授權說明：
  storybook.nlpi.edu.tw 保有著作權，不提供全文再利用授權。
  本爬蟲僅收集書名、作者、語言、適讀年齡等書目 metadata，
  body 欄位存放書名作為 placeholder，license_type = "research-only"。

執行模式：
  --mode dry-run    （預設）首頁可用性驗證 + 輸出觀測 JSON
  --mode metadata   全站分頁爬取 → data/raw/yuanmeng_metadata.jsonl

使用方式（建議透過 Makefile）：
  python -m crawlers.tier1.yuanmeng.yuanmeng_crawler --mode metadata
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from crawlers.config import USER_AGENT

BASE_URL = "https://storybook.nlpi.edu.tw/"
LISTING_URL = "https://storybook.nlpi.edu.tw/all-books.aspx"
OUTPUT_PATH = Path("data/raw/yuanmeng_dry_run.json")
METADATA_OUTPUT_PATH = Path("data/raw/yuanmeng_metadata.jsonl")

# 語言文字 → schema language code
_LANG_MAP: dict[str, str] = {
    "中文": "zh-TW",
    "國語": "zh-TW",
    "華語": "zh-TW",
    "台語": "nan-TW",
    "臺語": "nan-TW",
    "閩南語": "nan-TW",
    "客語": "hak-TW",
    "客家語": "hak-TW",
    "原住民": "indigenous",
}


def _url_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:6]


def parse_book_id(onclick: str) -> str | None:
    """Extract book NO from onclick string like openWindow('playbook2.aspx?NO=123')."""
    m = re.search(r"NO=(\d+)", onclick)
    return m.group(1) if m else None


def map_language(lang_text: str) -> str:
    """Map language badge text to schema language code; defaults to zh-TW."""
    for keyword, code in _LANG_MAP.items():
        if keyword in lang_text:
            return code
    return "zh-TW"


def parse_age_range(age_text: str) -> dict:
    """Parse age range text like '7-9歲' into {min, max}; defaults to {0, 12}."""
    m = re.search(r"(\d+)[^\d]+(\d+)", age_text)
    if m:
        return {"min": max(0, int(m.group(1))), "max": min(int(m.group(2)), 12)}
    return {"min": 0, "max": 12}


def normalize_book_record(card_data: dict, index: int) -> dict | None:
    """Build a corpus schema record from listing-page card data.

    Returns None when book_id cannot be extracted (book is unidentifiable).
    body = title because full text is All Rights Reserved.
    """
    title = card_data.get("title") or f"YM book {index}"
    onclick = card_data.get("onclick", "")
    book_id = parse_book_id(onclick)
    if not book_id:
        logging.warning("Skipping card (no book_id): %s", title)
        return None

    source_url = f"https://storybook.nlpi.edu.tw/book-single.aspx?BookNO={book_id}"
    language = map_language(card_data.get("language", ""))
    age_range = parse_age_range(card_data.get("age_text", ""))

    return {
        "id": f"YM-{_url_id(source_url)}",
        "source": "YUANMENG",
        "source_url": source_url,
        "content_type": "picture_book",
        "language": [language],
        "title": title,
        "body": title,
        "age_range": age_range,
        "developmental_milestone": [],
        "phonics": {},
        "themes": [],
        "action_cues": [],
        "word_count": len(title),
        "has_audio": False,
        "license_type": "research-only",
        "license": "All Rights Reserved - metadata only (國立公共資訊圖書館)",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "raw_metadata": {
            "book_id": book_id,
            "author": card_data.get("author", ""),
            "language_text": card_data.get("language", ""),
        },
    }


def filter_book_links(anchor_data: list[dict]) -> list[dict]:
    """Filter anchor data for book-related links. Testable pure function."""
    results = [
        item for item in anchor_data
        if "book" in item.get("href", "") or "all-books" in item.get("href", "")
    ]
    return results[:20]


def filter_pagination(node_data: list[dict]) -> list[dict]:
    """Filter pagination candidates. Testable pure function."""
    results = [
        item for item in node_data
        if re.search(r'下一頁|next|page', item.get("text", ""), re.IGNORECASE)
        or re.search(r'page', item.get("href", ""), re.IGNORECASE)
    ]
    return results[:10]


def build_dry_run_payload(
    base_url: str,
    title: str,
    book_links: list[dict],
    pagination: list[dict],
) -> dict:
    """Assemble dry-run output from parsed results. Testable pure function."""
    return {
        "base_url": base_url,
        "title": title,
        "book_link_count": len(book_links),
        "book_links": [
            {"text": item.get("text", ""), "url": urljoin(base_url, item.get("href", ""))}
            for item in book_links
        ],
        "pagination_candidates": pagination,
    }


async def run(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=USER_AGENT)
            await page.goto(BASE_URL, wait_until="networkidle")

            title = await page.title()
            all_anchors = await page.eval_on_selector_all(
                "a[href]",
                """
                (anchors) => anchors.map((a) => ({
                    href: a.getAttribute('href') || '',
                    text: (a.textContent || '').trim()
                }))
                """,
            )
            all_nodes = await page.eval_on_selector_all(
                "a[href], button",
                """
                (nodes) => nodes.map((n) => ({
                    text: (n.textContent || '').trim(),
                    href: n.getAttribute ? (n.getAttribute('href') || '') : ''
                }))
                """,
            )

            book_links = filter_book_links(all_anchors)
            pagination = filter_pagination(all_nodes)
            payload = build_dry_run_payload(BASE_URL, title, book_links, pagination)

            output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            await browser.close()


def _write_jsonl(output: Path, records: list[dict]) -> None:
    with output.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


async def run_metadata(output: Path, max_pages: int = 50) -> None:
    """Paginate all-books listing and emit corpus schema JSONL (metadata only).

    Args:
        output: Destination JSONL path.
        max_pages: Upper bound on page iterations (default 50).

    Termination: stops early when a page returns 0 cards or all cards on a
    page are already seen (deduped). Partial results are written on exception.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page(user_agent=USER_AGENT)
            seen_ids: set[str] = set()

            for page_num in range(1, max_pages + 1):
                url = f"{LISTING_URL}?p={page_num}"
                await page.goto(url, wait_until="networkidle")

                cards = await page.eval_on_selector_all(
                    "div.card.book-card",
                    """(cards) => cards.map(c => ({
                        title: (c.querySelector('a.card-title') || {textContent:''}).textContent.trim(),
                        author: (c.querySelector('p.work-author') || {textContent:''}).textContent.trim(),
                        language: (c.querySelector('p.book-lang') || {textContent:''}).textContent.trim(),
                        onclick: (c.querySelector('a[onclick]') || {}).getAttribute
                                  ? (c.querySelector('a[onclick]').getAttribute('onclick') || '')
                                  : '',
                        age_text: Array.from(c.querySelectorAll('p.work-des a'))
                                       .map(a => a.textContent.trim()).join(' ')
                    }))""",
                )

                if not cards:
                    break

                new_on_page = 0
                for i, card in enumerate(cards):
                    index = len(records) + 1
                    record = normalize_book_record(card, index)
                    if record and record["id"] not in seen_ids:
                        seen_ids.add(record["id"])
                        records.append(record)
                        new_on_page += 1

                if new_on_page == 0:
                    break
        except Exception:
            logging.warning("run_metadata interrupted; writing %d partial records", len(records))
            _write_jsonl(output, records)
            raise
        finally:
            await browser.close()

    _write_jsonl(output, records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["dry-run", "metadata"],
        default="dry-run",
        help="dry-run: 首頁可用性檢查; metadata: 全站分頁爬取",
    )
    parser.add_argument("--output", default=None)
    parser.add_argument("--max-pages", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.mode == "metadata":
        out = Path(args.output) if args.output else METADATA_OUTPUT_PATH
        asyncio.run(run_metadata(out, max_pages=args.max_pages))
    else:
        out = Path(args.output) if args.output else OUTPUT_PATH
        asyncio.run(run(out))


if __name__ == "__main__":
    main()
