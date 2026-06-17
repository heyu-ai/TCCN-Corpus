PYTHON ?= $(shell command -v python3 2>/dev/null || command -v /home/node/bin/python3 2>/dev/null || command -v python 2>/dev/null)

.PHONY: test test-unit check-python ogd-check robots-check schema-check

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
