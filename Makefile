PYTHON ?= $(shell command -v uv >/dev/null 2>&1 && echo "uv run python" || command -v python3 2>/dev/null || command -v /home/node/bin/python3 2>/dev/null || command -v python 2>/dev/null)

.PHONY: test test-unit check-python ogd-check robots-check schema-check crawl-moc crawl-moc-song crawl-yuanmeng phase2-check phase3-check clean-data label-data phase4-check extract-song-lyrics phase5-check

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
	SCRAPY_SETTINGS_MODULE=crawlers.tier1.moc_children.settings \
		$(PYTHON) -m scrapy runspider \
		crawlers/tier1/moc_children/spiders/listing_spider.py \
		-O data/raw/moc_listing.jsonl:jsonlines

# Phase 3: 文化部兒童文化館兒歌爬取（四語言分類）
crawl-moc-song: check-python
	SCRAPY_SETTINGS_MODULE=crawlers.tier1.moc_children.settings \
		$(PYTHON) -m scrapy runspider \
		crawlers/tier1/moc_children/spiders/song_spider.py \
		-O data/raw/moc_song.jsonl:jsonlines

# Phase 3: 圓夢繪本全站書目 metadata（All Rights Reserved，license_type=research-only）
crawl-yuanmeng: check-python
	$(PYTHON) -m crawlers.tier1.yuanmeng.yuanmeng_crawler --mode metadata \
		--output data/raw/yuanmeng_metadata.jsonl

# Phase 2: 爬取後驗證 Schema 對齊度
phase2-check: schema-check
	@echo "--- Phase 2 Schema alignment check done ---"

# Phase 3: 爬取後驗證 Schema 對齊度（含兒歌）
phase3-check: schema-check
	@echo "--- Phase 3 Schema alignment check done ---"

# Phase 4: 清洗 data/raw/*.jsonl → data/cleaned/
clean-data: check-python
	$(PYTHON) scripts/clean.py

# Phase 4: 標籤化 data/cleaned/*.jsonl → data/labeled/（依賴 clean-data，確保序列執行）
label-data: check-python clean-data
	$(PYTHON) scripts/label.py

# Phase 5a: 下載兒歌 PDF 萃取歌詞，原地回填 data/raw/moc_song.jsonl（需先執行 crawl-moc-song）
extract-song-lyrics: check-python
	$(PYTHON) scripts/extract_song_lyrics.py

# Phase 5a: 萃取歌詞 + Phase 4 pipeline 驗證（需先執行 crawl-moc-song）
phase5-check: check-python
	$(MAKE) extract-song-lyrics
	$(MAKE) phase4-check
	@echo "--- Phase 5a Song lyrics extraction + pipeline check done ---"

# Phase 4: 清洗 + 標籤化 + Schema 驗證
phase4-check: label-data
	@set -- data/labeled/*.jsonl; \
	if [ ! -e "$$1" ]; then \
		echo "[SKIP] data/labeled/*.jsonl 不存在，先執行 make label-data。"; \
	else \
		$(PYTHON) -m schemas.validate "$$@" && echo "--- Phase 4 Schema alignment check done ---"; \
	fi
