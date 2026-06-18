# Changelog

本專案版本遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [Unreleased] - Phase 2: 爬蟲開發與測試

### Added
- `crawlers/tier1/moc_children/spiders/listing_spider.py`：直接從
  `children.moc.gov.tw/animate_list` 列表頁爬取動畫書目，作為 OGD 資料集下架後
  的替代 seed 產生器。提供 `extract_book_links`、`next_page_url`、`build_raw_record`、
  `normalize_listing_record` 等純函式（可獨立測試）。
- `crawlers/tier1/yuanmeng/yuanmeng_crawler.py`：新增 `filter_book_links`、
  `filter_pagination`、`build_dry_run_payload` 三個純函式，解耦 Playwright I/O，
  提高可測試性。
- `make crawl-moc`：執行 listing_spider，輸出 `data/raw/moc_listing.jsonl`。
- `make crawl-yuanmeng`：執行圓夢繪本 metadata dry-run。
- `make phase2-check`：爬取後執行 Schema 對齊驗證。
- `tests/test_listing_spider.py`：10 個測試，涵蓋連結萃取、去重、外域過濾、
  分頁 URL 解析、HTML 標題/內文擷取、Schema 對齊。
- `tests/test_yuanmeng_crawler.py`：6 個測試，涵蓋書籍連結過濾、分頁偵測、
  dry-run payload 結構。
- `tests/test_animate_spider.py`：新增 3 個 `parse_detail` 測試（h1 標題萃取、
  seed 標題 fallback、段落內文合併）。

### Changed
- `crawlers/tier1/moc_children/settings.py`：改用 `import crawlers.config as _config`
  並明確賦值為 Scrapy 設定常數，消除 ruff F401 lint 警告。

## [0.1.1] - 2026-06-17

### Added
- Phase 1 合規審查與 Schema 鎖定（Issue #4）。
- `schemas/validate.py`：依 `corpus_schema.json` 驗證單筆/JSONL 記錄的工具與 CLER（CLI），啟用 `format`（uri / date-time）檢查。
- `make schema-check`、`make robots-check` 兩個 Makefile target。
- `corpus_schema.json` 嚴格鎖定：頂層與 `age_range` / `phonics` 加 `additionalProperties: false`。

### Changed
- `scripts/check_robots.py` 改用 `crawlers.config` 共用 `User-Agent`，消除組織 URL 漂移。
- `pyproject.toml`：新增 `jsonschema[format-nongpl]` 相依，並以 package-data 確保 `corpus_schema.json` 隨套件發佈。

### Fixed
- `make robots-check` 在乾淨 checkout（無 editable install）下的 `ModuleNotFoundError`（改用 `-m` module mode）。
- `make schema-check` 改用 shell glob，避免檔名含空白時 word-splitting 假性失敗。

### Docs
- `docs/data-sources.md`：記錄 2026-06-16 robots.txt 重測、文化部 OGD 三筆資料集（#24973 / #24968 / #113587）已下架的 blocker。
