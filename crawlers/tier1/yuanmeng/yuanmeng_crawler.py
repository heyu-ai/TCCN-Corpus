"""
Yuanmeng metadata-only dry-run crawler.

用途：
- 驗證首頁是否可正常載入
- 檢查分頁元素與書籍連結 selector 是否存在
- 不抓全文，只輸出 metadata 觀測結果
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

BASE_URL = "https://storybook.nlpi.edu.tw/"
OUTPUT_PATH = Path("data/raw/yuanmeng_dry_run.json")
USER_AGENT = "TCCN-Corpus-Bot/1.0 (+https://github.com/howie/TCCN-Corpus)"


async def run(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto(BASE_URL, wait_until="networkidle")

        title = await page.title()
        candidate_links = await page.eval_on_selector_all(
            "a[href]",
            """
            (anchors) => anchors
              .map((anchor) => ({
                href: anchor.getAttribute('href') || '',
                text: (anchor.textContent || '').trim()
              }))
              .filter((item) => item.href.includes('book') || item.href.includes('all-books'))
              .slice(0, 20)
            """,
        )
        pagination_links = await page.eval_on_selector_all(
            "a[href], button",
            """
            (nodes) => nodes
              .map((node) => ({
                text: (node.textContent || '').trim(),
                href: node.getAttribute ? (node.getAttribute('href') || '') : ''
              }))
              .filter((item) => /下一頁|next|page/i.test(item.text) || /page/i.test(item.href))
              .slice(0, 10)
            """,
        )

        payload = {
            "base_url": BASE_URL,
            "title": title,
            "book_link_count": len(candidate_links),
            "book_links": [
                {"text": item["text"], "url": urljoin(BASE_URL, item["href"])}
                for item in candidate_links
            ],
            "pagination_candidates": pagination_links,
        }
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
