"""
從文化部 OGD / data.gov.tw 資料集中抓取動畫書目 JSON，並轉成統一 JSONL。

優先順序：
1. --resource-url 或 MOC_OGD_RESOURCE_URL
2. --dataset-url 或 MOC_OGD_DATASET_URL（自頁面找第一個 JSON 資源）
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

import jsonlines
import requests
from bs4 import BeautifulSoup

from crawlers.config import USER_AGENT

DEFAULT_OUTPUT = Path("data/raw/moc_ogd.jsonl")
TIMEOUT = 30


@dataclass
class FetchConfig:
    resource_url: str | None
    dataset_url: str | None
    output: Path
    check_only: bool


def parse_args() -> FetchConfig:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resource-url", default=os.getenv("MOC_OGD_RESOURCE_URL"))
    parser.add_argument("--dataset-url", default=os.getenv("MOC_OGD_DATASET_URL"))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="只解析 dataset/resource URL 並輸出檢查結果，不抓資料、不寫檔。",
    )
    args = parser.parse_args()
    return FetchConfig(
        resource_url=args.resource_url,
        dataset_url=args.dataset_url,
        output=Path(args.output),
        check_only=args.check_only,
    )


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json,text/html"})
    return session


def discover_resource_url(session: requests.Session, dataset_url: str) -> str:
    response = session.get(dataset_url, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for anchor in soup.select("a[href], a[data-url]"):
        href = (anchor.get("href") or anchor.get("data-url") or "").strip()
        label = anchor.get_text(" ", strip=True).lower()
        if ".json" in href.lower() or "json" in label:
            return urljoin(dataset_url, href)

    # Some CKAN pages keep resource links in scripts instead of visible anchors.
    for match in re.finditer(r'https?://[^"\'\s>]+\.json(?:\?[^"\'\s>]*)?', response.text, flags=re.IGNORECASE):
        return match.group(0)

    hinted_url = discover_from_ckan_api(session, dataset_url)
    if hinted_url:
        return hinted_url

    raise RuntimeError(
        "無法從 data.gov.tw dataset 頁面找到 JSON 資源 URL。"
        "請改用 --resource-url 或設定 MOC_OGD_RESOURCE_URL。"
    )


def discover_from_ckan_api(session: requests.Session, dataset_url: str) -> str | None:
    hint = dataset_hint_from_url(dataset_url)
    if not hint:
        return None
    api_url = "https://data.gov.tw/api/3/action/package_search"
    params = {"q": hint, "rows": 5}
    response = session.get(api_url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    for result in payload.get("result", {}).get("results", []):
        for resource in result.get("resources", []):
            url = str(resource.get("url") or "").strip()
            fmt = str(resource.get("format") or "").lower()
            name = str(resource.get("name") or "").lower()
            if not url:
                continue
            if ".json" in url.lower() or "json" in fmt or "json" in name:
                return url
    return None


def dataset_hint_from_url(dataset_url: str) -> str:
    parsed = urlparse(dataset_url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    if not segments:
        return ""
    if "dataset" in segments:
        idx = segments.index("dataset")
        if idx + 1 < len(segments):
            return segments[idx + 1]
    return segments[-1]


def fetch_payload(session: requests.Session, resource_url: str) -> Any:
    response = session.get(resource_url, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def iter_records(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(payload, dict):
        raise TypeError(f"不支援的 payload 型別：{type(payload)!r}")

    for key in ("data", "result", "results", "items", "records"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict):
                    yield item
            return
        if isinstance(candidate, dict):
            nested = candidate.get("records") or candidate.get("items") or candidate.get("data")
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        yield item
                return

    raise KeyError("找不到可迭代的 records/data/items/result 欄位。")


def pick_first(record: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value)
    return default


def infer_languages(record: dict[str, Any]) -> list[str]:
    combined = " ".join(
        pick_first(record, key)
        for key in ("language", "語言", "適用語言", "book_language", "category")
    ).lower()
    languages: list[str] = []
    if any(token in combined for token in ("台語", "閩南", "nan")):
        languages.append("nan-TW")
    if any(token in combined for token in ("客語", "hak")):
        languages.append("hak-TW")
    if any(token in combined for token in ("原住民", "indigenous")):
        languages.append("indigenous")
    if not languages:
        languages.append("zh-TW")
    return languages


def infer_age_range(record: dict[str, Any]) -> dict[str, int]:
    age_text = " ".join(
        pick_first(record, key)
        for key in ("age", "適讀年齡", "閱讀分級", "reader_age", "grade")
    )
    if "0-6" in age_text or "0~6" in age_text:
        return {"min": 0, "max": 6}
    if "7-9" in age_text or "7~9" in age_text:
        return {"min": 7, "max": 9}
    if "10-12" in age_text or "10~12" in age_text:
        return {"min": 10, "max": 12}
    return {"min": 0, "max": 12}


def normalize_record(record: dict[str, Any], index: int) -> dict[str, Any]:
    title = pick_first(record, "title", "name", "書名", "動畫名稱", "作品名稱")
    body = pick_first(
        record,
        "description",
        "summary",
        "簡介",
        "內容簡介",
        "story",
        "劇情簡介",
        default=title,
    )
    source_url = pick_first(record, "url", "link", "網址", "作品網址", "source_url")
    collected_at = datetime.now(timezone.utc).isoformat()
    themes_text = pick_first(record, "theme", "主題", "category", "分類")
    themes = [item.strip() for item in themes_text.replace("、", ",").split(",") if item.strip()]

    return {
        "id": f"MOC-{index:06d}",
        "source": "MOC_CHILDREN",
        "source_url": source_url,
        "content_type": "animation_script",
        "language": infer_languages(record),
        "title": title or f"MOC entry {index}",
        "body": body,
        "age_range": infer_age_range(record),
        "developmental_milestone": [],
        "phonics": {},
        "themes": themes,
        "action_cues": [],
        "word_count": len(body),
        "has_audio": False,
        "license_type": "ogdl-tw-1",
        "license": "政府資料開放授權條款-第1版",
        "collected_at": collected_at,
        "raw_metadata": record,
    }


def write_jsonl(records: Iterable[dict[str, Any]], output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with jsonlines.open(output, mode="w") as writer:
        for count, record in enumerate(records, start=1):
            writer.write(record)
    return count


def resolve_resource_url(config: FetchConfig, session: requests.Session) -> str:
    if config.resource_url:
        return config.resource_url
    if config.dataset_url:
        return discover_resource_url(session, config.dataset_url)
    raise RuntimeError(
        "請提供 --resource-url / MOC_OGD_RESOURCE_URL，或提供 --dataset-url / MOC_OGD_DATASET_URL。"
    )


def main() -> None:
    config = parse_args()
    session = build_session()
    resource_url = resolve_resource_url(config, session)
    if config.check_only:
        print(
            json.dumps(
                {
                    "mode": "check-only",
                    "dataset_url": config.dataset_url,
                    "resource_url": resource_url,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    payload = fetch_payload(session, resource_url)
    normalized = (
        normalize_record(record, index)
        for index, record in enumerate(iter_records(payload), start=1)
    )
    written = write_jsonl(normalized, config.output)
    summary = {
        "resource_url": resource_url,
        "dataset_url": config.dataset_url,
        "output": str(config.output),
        "records": written,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
