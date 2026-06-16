import json

import jsonschema
import pytest

from crawlers.tier1.moc_children.ogd_fetcher import normalize_record
from schemas.validate import load_schema, validate_jsonl, validate_record


def make_valid_record() -> dict:
    return {
        "id": "MOC-000001",
        "source": "MOC_CHILDREN",
        "source_url": "https://children.moc.gov.tw/animate/1",
        "content_type": "story",
        "language": ["zh-TW"],
        "title": "小松鼠的冒險",
        "body": "從前有一隻小松鼠……",
        "age_range": {"min": 0, "max": 6},
        "developmental_milestone": ["language_3_4"],
        "phonics": {"rhyme_scheme": "AABB", "repetition_ratio": 0.5},
        "themes": ["友誼", "自然"],
        "action_cues": ["拍手"],
        "word_count": 12,
        "has_audio": False,
        "license": "政府資料開放授權條款-第1版",
        "license_type": "ogdl-tw-1",
        "collected_at": "2026-06-16T00:00:00+00:00",
        "raw_metadata": {"原始欄位": "值"},
    }


def test_load_schema_locks_additional_properties():
    schema = load_schema()
    assert schema["additionalProperties"] is False


def test_valid_golden_record_passes():
    validate_record(make_valid_record())


def test_normalize_record_output_matches_schema():
    record = {
        "title": "小鴨",
        "description": "一隻小鴨的故事",
        "url": "https://children.moc.gov.tw/animate/42",
        "語言": "台語",
        "適讀年齡": "0-6",
    }
    normalized = normalize_record(record, 1)
    # fetcher 產出必須與鎖定後的 schema 完全對齊（含 additionalProperties:false）。
    validate_record(normalized)


def test_missing_required_field_fails():
    record = make_valid_record()
    del record["license_type"]
    with pytest.raises(jsonschema.ValidationError):
        validate_record(record)


def test_unknown_field_fails_under_locked_schema():
    record = make_valid_record()
    record["unexpected_field"] = "x"
    with pytest.raises(jsonschema.ValidationError):
        validate_record(record)


def test_enum_violation_fails():
    record = make_valid_record()
    record["license_type"] = "unknown"
    with pytest.raises(jsonschema.ValidationError):
        validate_record(record)


def test_validate_jsonl_reports_pass_and_errors(tmp_path):
    good = make_valid_record()
    bad = make_valid_record()
    del bad["title"]
    path = tmp_path / "sample.jsonl"
    path.write_text(
        json.dumps(good, ensure_ascii=False) + "\n"
        + "\n"  # 空行應被略過
        + json.dumps(bad, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    passed, errors = validate_jsonl(path)
    assert passed == 1
    assert len(errors) == 1
    assert "第 3 行" in errors[0]
