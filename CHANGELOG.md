# Changelog

本專案版本遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

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
