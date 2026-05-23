from pathlib import Path

from crawlers.tier1.moc_children import ogd_fetcher
from crawlers.tier1.moc_children.ogd_fetcher import (
    dataset_hint_from_url,
    discover_resource_url,
    infer_languages,
    normalize_record,
    parse_args,
)
from crawlers.config import USER_AGENT


def test_infer_languages_detects_taiwanese_hokkien():
    record = {"語言": "台語"}
    assert infer_languages(record) == ["nan-TW"]


def test_normalize_record_sets_license_type_and_source():
    record = {"title": "小松鼠", "description": "測試簡介", "url": "https://example.com/story"}
    normalized = normalize_record(record, 1)
    assert normalized["id"] == "MOC-000001"
    assert normalized["source"] == "MOC_CHILDREN"
    assert normalized["license_type"] == "ogdl-tw-1"
    assert normalized["source_url"] == "https://example.com/story"


def test_user_agent_points_to_org_repo():
    assert "github.com/heyu-ai/TCCN-Corpus" in USER_AGENT


class DummyResponse:
    def __init__(self, text: str = "", payload: dict | None = None):
        self.text = text
        self._payload = payload or {}

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class DummySession:
    def __init__(self, responses: list[DummyResponse]):
        self.responses = responses
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url: str, params: dict | None = None, timeout: int | None = None) -> DummyResponse:
        del timeout
        self.calls.append((url, params))
        return self.responses.pop(0)


def test_discover_resource_url_from_anchor():
    html = '<a href="/resource/book.json">download json</a>'
    session = DummySession([DummyResponse(text=html)])
    url = discover_resource_url(session, "https://data.gov.tw/dataset/abc")
    assert url == "https://data.gov.tw/resource/book.json"


def test_discover_resource_url_from_script_json_url():
    html = '<script>const r = "https://example.org/files/moc.json?x=1";</script>'
    session = DummySession([DummyResponse(text=html)])
    url = discover_resource_url(session, "https://data.gov.tw/dataset/abc")
    assert url == "https://example.org/files/moc.json?x=1"


def test_discover_resource_url_from_ckan_api_fallback():
    html = "<html><body>no json link here</body></html>"
    ckan_payload = {
        "result": {
            "results": [
                {
                    "resources": [
                        {"url": "https://data.gov.tw/files/moc-data.csv", "format": "CSV"},
                        {"url": "https://data.gov.tw/files/moc-data.json", "format": "JSON"},
                    ]
                }
            ]
        }
    }
    session = DummySession([DummyResponse(text=html), DummyResponse(payload=ckan_payload)])
    url = discover_resource_url(session, "https://data.gov.tw/dataset/moc-child-books")
    assert url == "https://data.gov.tw/files/moc-data.json"
    assert session.calls[1][0] == "https://data.gov.tw/api/3/action/package_search"
    assert session.calls[1][1] == {"q": "moc-child-books", "rows": 5}


def test_dataset_hint_from_url_extracts_dataset_slug():
    hint = dataset_hint_from_url("https://data.gov.tw/dataset/moc-child-books")
    assert hint == "moc-child-books"


def test_parse_args_supports_check_only(monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "ogd_fetcher.py",
            "--dataset-url",
            "https://data.gov.tw/dataset/moc-child-books",
            "--check-only",
        ],
    )
    config = parse_args()
    assert config.dataset_url == "https://data.gov.tw/dataset/moc-child-books"
    assert config.output == Path("data/raw/moc_ogd.jsonl")
    assert config.check_only is True


def test_main_check_only_prints_without_writing(monkeypatch, capsys):
    monkeypatch.setattr(
        "sys.argv",
        [
            "ogd_fetcher.py",
            "--resource-url",
            "https://data.gov.tw/files/moc-data.json",
            "--check-only",
        ],
    )
    ogd_fetcher.main()
    output = capsys.readouterr().out
    assert '"mode": "check-only"' in output
    assert '"resource_url": "https://data.gov.tw/files/moc-data.json"' in output
