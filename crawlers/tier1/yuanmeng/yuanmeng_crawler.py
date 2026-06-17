"""
Yuanmeng metadata-only dry-run crawler.

用途：
- 驗證首頁是否可正常載入
- 檢查分頁元素與書籍連結 selector 是否存在
- 不抓全文，只輸出 metadata 觀測結果（授權限制：圓夢繪本 All Rights Reserved）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from crawlers.config import USER_AGENT

BASE_URL = "https://storybook.nlpi.edu.tw/"
OUTPUT_PATH = Path("data/raw/yuanmeng_dry_run.json")


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
        await browser.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run(Path(args.output)))


if __name__ == "__main__":
    main()
