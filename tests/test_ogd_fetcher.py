from crawlers.tier1.moc_children.ogd_fetcher import infer_languages, normalize_record
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
