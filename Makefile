PYTHON ?= $(shell command -v python3 2>/dev/null || command -v /home/node/bin/python3 2>/dev/null || command -v python 2>/dev/null)

.PHONY: test test-unit check-python ogd-check robots-check schema-check crawl-moc crawl-yuanmeng phase2-check

check-python:
	@test -n "$(PYTHON)" || (echo "python executable not found; set PYTHON=/path/to/python" >&2; exit 1)
	@$(PYTHON) --version

test test-unit: check-python
	$(PYTHON) -m pytest

ogd-check: check-python
	$(PYTHON) -m crawlers.tier1.moc_children.ogd_fetcher --check-only

robots-check: check-python
	$(PYTHON) -m scripts.check_robots

schema-check: check-python
	@set -- data/raw/*.jsonl; \
	if [ ! -e "$$1" ]; then \
		echo "[SKIP] data/raw/*.jsonl 不存在，尚無語料可驗證（先執行爬蟲產出 JSONL）。"; \
	else \
		$(PYTHON) -m schemas.validate "$$@"; \
	fi

# Phase 2: 直接從網站列表頁爬取（OGD data.gov.tw 資料集已下架）
crawl-moc: check-python
	$(PYTHON) -m scrapy runspider \
		crawlers/tier1/moc_children/spiders/listing_spider.py \
		-o data/raw/moc_listing.jsonl:jsonlines \
		-s SETTINGS_MODULE=crawlers.tier1.moc_children.settings

# Phase 2: 圓夢繪本 metadata dry-run（不抓全文）
crawl-yuanmeng: check-python
	$(PYTHON) -m crawlers.tier1.yuanmeng.yuanmeng_crawler

# Phase 2: 爬取後驗證 Schema 對齊度
phase2-check: schema-check
	@echo "--- Phase 2 Schema alignment check done ---"
