from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import scrapy


def load_seed_entries(seed_path: Path) -> list[dict]:
    if not seed_path.exists():
        raise FileNotFoundError(
            f"找不到 seed 檔案：{seed_path}。請先執行 ogd_fetcher.py 產生 data/raw/moc_ogd.jsonl。"
        )

    entries: list[dict] = []
    with seed_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries


class AnimateSpider(scrapy.Spider):
    name = "animate_spider"
    allowed_domains = ["children.moc.gov.tw"]
    custom_settings = {
        "USER_AGENT": "TCCN-Corpus-Bot/1.0 (+https://github.com/howie/TCCN-Corpus)",
        "DOWNLOAD_DELAY": 2.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def __init__(self, seed_file: str = "data/raw/moc_ogd.jsonl", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seed_file = Path(seed_file)

    def start_requests(self):
        for seed in load_seed_entries(self.seed_file):
            source_url = seed.get("source_url") or "https://children.moc.gov.tw/animate_list"
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
