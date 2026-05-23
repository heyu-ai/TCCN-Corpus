PYTHON ?= $(shell command -v python3 2>/dev/null || command -v /home/node/bin/python3 2>/dev/null || command -v python 2>/dev/null)

.PHONY: test test-unit check-python ogd-check

check-python:
	@test -n "$(PYTHON)" || (echo "python executable not found; set PYTHON=/path/to/python" >&2; exit 1)
	@$(PYTHON) --version

test test-unit: check-python
	$(PYTHON) -m pytest

ogd-check: check-python
	$(PYTHON) -m crawlers.tier1.moc_children.ogd_fetcher --check-only
