"""
直接從 children.moc.gov.tw 列表頁爬取動畫書目。

OGD data.gov.tw 三筆兒童文化館資料集已下架（2026-06-16 確認），無法透過
ogd_fetcher 取得 seed list。本 spider 直接爬取網站列表頁，產出與 ogd_fetcher
相同欄位集合的 data/raw/moc_listing.jsonl（language/themes/age_range 為硬編碼
預設值，非 metadata 推算）。

使用方式（OGD 可用時改用 ogd_fetcher + animate_spider；建議透過 Makefile 執行）：
  SCRAPY_SETTINGS_MODULE=crawlers.tier1.moc_children.settings \\
    python -m scrapy runspider crawlers/tier1/moc_children/spiders/listing_spider.py \\
    -O data/raw/moc_listing.jsonl:jsonlines
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import urlparse

import scrapy

from crawlers.config import CONCURRENT_REQUESTS_PER_DOMAIN, DOWNLOAD_DELAY, USER_AGENT

LIST_URL = "https://children.moc.gov.tw/animate_list"


def extract_book_links(response) -> list[str]:
    """Extract absolute book-detail URLs from a listing-page response."""
    hrefs = response.css(
        "a.animate-item::attr(href),"
        "a.book-item::attr(href),"
        ".item-list a::attr(href),"
        "ul.list a::attr(href),"
        "table.items td a::attr(href)"
    ).getall()
    seen: set[str] = set()
    urls: list[str] = []
    for href in hrefs:
        href = href.strip()
        if not href or href == "#":
            continue
        absolute = response.urljoin(href)
        if urlparse(absolute).hostname == "children.moc.gov.tw" and absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls


def next_page_url(response) -> str | None:
    """Return the next-page URL from pagination, or None if last page."""
    href = response.css(
        "a.next::attr(href),"
        "a[rel='next']::attr(href),"
        ".pagination a:last-child::attr(href),"
        "a:contains('下一頁')::attr(href)"
    ).get()
    if not href or not href.strip():
        return None
    absolute = response.urljoin(href.strip())
    return absolute if absolute != response.url else None


def build_raw_record(response) -> dict:
    """Extract raw fields from a detail-page response."""
    title = (
        response.css("h1::text, h2::text, .title::text, .page-title::text").get() or ""
    ).strip()
    paragraphs = response.css(
        "main p::text, article p::text, .content p::text, .editor p::text"
    ).getall()
    body = "\n".join(p.strip() for p in paragraphs if p.strip())
    return {
        "title": title,
        "description": body or title,
        "url": response.url,
    }


def _url_id(url: str) -> str:
    """Derive a stable 6-char hex ID suffix from a URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:6]


def normalize_listing_record(raw: dict, index: int) -> dict:
    """Convert a raw detail-page record to corpus schema format."""
    title = raw.get("title") or f"MOC listing {index}"
    body = raw.get("description") or title
    url = raw.get("url") or ""
    record_id = f"MOC-{_url_id(url)}" if url else f"MOC-{index:06d}"
    record: dict = {
        "id": record_id,
        "source": "MOC_CHILDREN",
        "content_type": "animation_script",
        "language": ["zh-TW"],
        "title": title,
        "body": body,
        "age_range": {"min": 0, "max": 12},
        "developmental_milestone": [],
        "phonics": {},
        "themes": [],
        "action_cues": [],
        "word_count": len(body),
        "has_audio": False,
        "license_type": "ogdl-tw-1",
        "license": "政府資料開放授權條款-第1版",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "raw_metadata": raw,
    }
    if url:
        record["source_url"] = url
    return record


class ListingSpider(scrapy.Spider):
    """
    直接從文化部兒童文化館列表頁爬取動畫書目，產出 schema-valid JSONL。

    OGD 下架後的主要爬取入口。使用 scrapy runspider 執行；
    輸出格式與 ogd_fetcher 一致，可直接餵給 animate_spider.py 作 seed。
    """

    name = "listing_spider"
    allowed_domains = ["children.moc.gov.tw"]
    start_urls = [LIST_URL]
    custom_settings = {
        "USER_AGENT": USER_AGENT,
        "DOWNLOAD_DELAY": DOWNLOAD_DELAY,
        "CONCURRENT_REQUESTS_PER_DOMAIN": CONCURRENT_REQUESTS_PER_DOMAIN,
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._counter = 0

    def parse(self, response) -> Iterator[dict]:
        book_links = extract_book_links(response)
        if not book_links:
            self.logger.warning("No book links found on %s — check CSS selectors", response.url)
        for url in book_links:
            yield response.follow(url, callback=self.parse_detail)

        nxt = next_page_url(response)
        if nxt:
            yield response.follow(nxt, callback=self.parse)

    def parse_detail(self, response) -> Iterator[dict]:
        self._counter += 1
        raw = build_raw_record(response)
        yield normalize_listing_record(raw, self._counter)
