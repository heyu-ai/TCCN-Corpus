"""
直接從 children.moc.gov.tw/song_list 爬取兒歌書目。

OGD 資料集已下架；本 spider 直接爬取網站列表頁，依語言分類（華語/台語/
客語/原住民語）產出 corpus schema 格式的 data/raw/moc_song.jsonl。

注意：歌詞全文需透過 /resource/song_pdf/{id}.pdf 下載，
      目前 body 欄位存放標題；PDF 萃取保留為後續階段。

使用方式（建議透過 Makefile 執行）：
  SCRAPY_SETTINGS_MODULE=crawlers.tier1.moc_children.settings \\
    python -m scrapy runspider crawlers/tier1/moc_children/spiders/song_spider.py \\
    -O data/raw/moc_song.jsonl:jsonlines
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Iterator
from urllib.parse import urlparse

import scrapy

from crawlers.config import CONCURRENT_REQUESTS_PER_DOMAIN, DOWNLOAD_DELAY, USER_AGENT

SONG_LIST_URL = "https://children.moc.gov.tw/song_list"

# language= param → schema language code + display name
LANGUAGE_SEEDS: list[tuple[str, str, str]] = [
    ("1", "zh-TW", "華語"),
    ("2", "nan-TW", "台語"),
    ("3", "hak-TW", "客語"),
    ("4", "indigenous", "原住民族語"),
]

# 類別 value substring → schema code (fallback for detail-page inference)
_LANG_MAP: dict[str, str] = {
    "華語": "zh-TW",
    "國語": "zh-TW",
    "台語": "nan-TW",
    "臺語": "nan-TW",
    "閩南語": "nan-TW",
    "客語": "hak-TW",
    "客家語": "hak-TW",
    "原住民": "indigenous",
}


def _url_id(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:6]


def extract_song_links(response) -> list[str]:
    """Extract absolute song-detail URLs from a listing-page response."""
    hrefs = response.css("a[href^='/song/']::attr(href)").getall()
    seen: set[str] = set()
    urls: list[str] = []
    for href in hrefs:
        absolute = response.urljoin(href.strip())
        if urlparse(absolute).hostname == "children.moc.gov.tw" and absolute not in seen:
            seen.add(absolute)
            urls.append(absolute)
    return urls


def next_page_url(response) -> str | None:
    """Return the next-page URL from pagination, or None if last page."""
    href = response.css(
        "a.next::attr(href),"
        "a[rel='next']::attr(href),"
        "a:contains('下一頁')::attr(href)"
    ).get()
    if not href or not href.strip():
        return None
    absolute = response.urljoin(href.strip())
    return absolute if absolute != response.url else None


def infer_language_from_meta(response) -> str:
    """Infer language code from detail-page 類別 metadata."""
    meta_items = response.css("ul li::text").getall()
    for text in meta_items:
        text = text.strip()
        if "類別" in text:
            for keyword, code in _LANG_MAP.items():
                if keyword in text:
                    return code
    return "zh-TW"


def extract_metadata(response) -> dict:
    """Parse metadata list (作曲/作詞/演唱) from detail page."""
    result: dict = {}
    for item in response.css("ul li::text").getall():
        item = item.strip()
        for field, key in (("作曲", "composer"), ("作詞", "lyricist"), ("演唱", "singer"), ("類別", "category")):
            if item.startswith(field):
                result[key] = re.sub(rf"^{field}[：:]\s*", "", item).strip()
    return result


def normalize_song_record(
    response,
    language: str,
    meta: dict,
    index: int,
) -> dict:
    """Build a corpus schema record from a song detail page."""
    url = response.url
    title = (response.css("h1::text").get() or "").strip() or f"MOC song {index}"
    body = title  # lyrics require PDF extraction (Phase 4)

    pdf_href = response.css("a[href*='song_pdf']::attr(href)").get() or ""
    pdf_url = response.urljoin(pdf_href) if pdf_href else ""

    raw: dict = {
        "url": url,
        "title": title,
        "composer": meta.get("composer", ""),
        "lyricist": meta.get("lyricist", ""),
        "singer": meta.get("singer", ""),
        "category": meta.get("category", ""),
        "sheet_music_url": pdf_url,
    }

    record: dict = {
        "id": f"MOC-{_url_id(url)}",
        "source": "MOC_CHILDREN",
        "source_url": url,
        "content_type": "nursery_rhyme",
        "language": [language],
        "title": title,
        "body": body,
        "age_range": {"min": 0, "max": 12},
        "developmental_milestone": [],
        "phonics": {},
        "themes": [],
        "action_cues": [],
        "word_count": len(body),
        "has_audio": True,
        "license_type": "ogdl-tw-1",
        "license": "政府資料開放授權條款-第1版",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "raw_metadata": raw,
    }
    return record


class SongSpider(scrapy.Spider):
    """
    爬取文化部兒童文化館兒歌書目（/song_list），依語言分四類爬取。

    爬取策略：
    - 以 ?language=1~4 分別爬取四種語言分類，確保語言標籤正確
    - 使用 URL hash 作為穩定 ID（MOC-{sha256[:6]}）
    - 目前 body = 標題（歌詞全文需 PDF 萃取，保留為後續階段）
    """

    name = "song_spider"
    allowed_domains = ["children.moc.gov.tw"]
    custom_settings = {
        "USER_AGENT": USER_AGENT,
        "DOWNLOAD_DELAY": DOWNLOAD_DELAY,
        "CONCURRENT_REQUESTS_PER_DOMAIN": CONCURRENT_REQUESTS_PER_DOMAIN,
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._counter = 0
        self._seen_urls: set[str] = set()

    def start_requests(self):
        for lang_param, lang_code, _ in LANGUAGE_SEEDS:
            url = f"{SONG_LIST_URL}?language={lang_param}"
            yield scrapy.Request(url, callback=self.parse, cb_kwargs={"language": lang_code})

    def parse(self, response, language: str) -> Iterator:
        urls = extract_song_links(response)
        if not urls:
            self.logger.warning(
                "No song links found on %s — check CSS selectors", response.url
            )
        for url in urls:
            if url not in self._seen_urls:
                self._seen_urls.add(url)
                yield response.follow(
                    url,
                    callback=self.parse_detail,
                    cb_kwargs={"language": language},
                )

        nxt = next_page_url(response)
        if nxt:
            yield response.follow(nxt, callback=self.parse, cb_kwargs={"language": language})

    def parse_detail(self, response, language: str) -> Iterator[dict]:
        self._counter += 1
        lang = infer_language_from_meta(response) or language
        meta = extract_metadata(response)
        yield normalize_song_record(response, lang, meta, self._counter)
