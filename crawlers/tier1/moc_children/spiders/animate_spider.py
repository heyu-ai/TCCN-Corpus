from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

import scrapy

from crawlers.config import CONCURRENT_REQUESTS_PER_DOMAIN, DOWNLOAD_DELAY, USER_AGENT


LOGGER = logging.getLogger(__name__)
DEFAULT_LIST_URL = "https://children.moc.gov.tw/animate_list"


def is_allowed_source_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host == "children.moc.gov.tw"


def iter_seed_entries(seed_path: Path) -> Iterator[dict]:
    if not seed_path.exists():
        raise FileNotFoundError(
            f"找不到 seed 檔案：{seed_path}。請先執行 ogd_fetcher.py 產生 data/raw/moc_ogd.jsonl。"
        )

    with seed_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                LOGGER.warning("略過無效 JSON seed（line=%s）", line_no)
                continue
            if not isinstance(entry, dict):
                LOGGER.warning("略過非物件 seed（line=%s, type=%s）", line_no, type(entry).__name__)
                continue
            yield entry


class AnimateSpider(scrapy.Spider):
    name = "animate_spider"
    allowed_domains = ["children.moc.gov.tw"]
    custom_settings = {
        "USER_AGENT": USER_AGENT,
        "DOWNLOAD_DELAY": DOWNLOAD_DELAY,
        "CONCURRENT_REQUESTS_PER_DOMAIN": CONCURRENT_REQUESTS_PER_DOMAIN,
    }

    def __init__(self, seed_file: str = "data/raw/moc_ogd.jsonl", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seed_file = Path(seed_file)

    def start_requests(self):
        for seed in iter_seed_entries(self.seed_file):
            source_url = seed.get("source_url") or DEFAULT_LIST_URL
            if not is_allowed_source_url(source_url):
                source_url = DEFAULT_LIST_URL
            yield scrapy.Request(source_url, callback=self.parse_detail, cb_kwargs={"seed": seed})

    def parse_detail(self, response: scrapy.http.Response, seed: dict):
        title = (
            response.css("h1::text, h2::text, .title::text, .page-title::text").get()
            or seed.get("title")
            or ""
        ).strip()
        paragraphs = response.css("main p::text, article p::text, .content p::text, .editor p::text").getall()
        body = "\n".join(part.strip() for part in paragraphs if part.strip()) or seed.get("body", "")
        yield {
            **seed,
            "title": title or seed.get("title"),
            "body": body,
            "source_url": response.url,
            "word_count": len(body),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
