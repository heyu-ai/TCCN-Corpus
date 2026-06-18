import json

import pytest

from scripts.clean import clean_body, normalize_fullwidth, process_file


def test_normalize_fullwidth_ascii():
    assert normalize_fullwidth("Ａ！") == "A!"


def test_normalize_fullwidth_tilde():
    assert normalize_fullwidth("～") == "~"


def test_normalize_fullwidth_ideographic_space():
    assert normalize_fullwidth("　") == " "


def test_normalize_fullwidth_leaves_cjk_untouched():
    assert normalize_fullwidth("你好") == "你好"


def test_clean_body_removes_control_chars():
    assert "\x01" not in clean_body("a\x01b")
    assert "\x0b" not in clean_body("a\x0bb")


def test_clean_body_collapses_excess_whitespace():
    assert clean_body("a\n\n\n\nb") == "a\n\nb"


def test_clean_body_decodes_html_entity_amp():
    assert clean_body("a &amp; b") == "a & b"


def test_clean_body_decodes_html_entity_lt_gt():
    assert clean_body("&lt;div&gt;") == "<div>"


def test_clean_body_strips_leading_trailing():
    assert clean_body("  hello  ") == "hello"


def test_clean_body_normalizes_fullwidth_inside():
    assert clean_body("Ａ") == "A"


def test_clean_body_empty_string():
    assert clean_body("") == ""


def test_clean_body_nbsp_normalized_to_space():
    assert clean_body("a&nbsp;b") == "a b"


def test_clean_body_multiple_nbsp_not_collapsed_to_newline():
    # 2 NBSP should become 2 spaces, not \n\n
    assert clean_body("a&nbsp;&nbsp;b") == "a  b"


def test_clean_body_three_nbsp_collapse_to_paragraph():
    # after NBSP→space, \s{3,} collapses 3 spaces to \n\n
    assert clean_body("a&nbsp;&nbsp;&nbsp;b") == "a\n\nb"


# --- process_file integration ---

@pytest.fixture()
def raw_dir(tmp_path, monkeypatch):
    """Redirect CLEANED_DIR to tmp_path and return a raw source dir."""
    src_dir = tmp_path / "raw"
    src_dir.mkdir()
    dst_dir = tmp_path / "cleaned"
    monkeypatch.setattr("scripts.clean.CLEANED_DIR", dst_dir)
    return src_dir, dst_dir


def test_process_file_roundtrip(raw_dir):
    src_dir, dst_dir = raw_dir
    src = src_dir / "test.jsonl"
    src.write_text('{"title":"A","body":"hello","content_type":"picture_book"}\n', encoding="utf-8")
    process_file(src)
    lines = (dst_dir / "test.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["body"] == "hello"
    assert "cleaned_at" in record
    assert record["word_count"] == 5


def test_process_file_nbsp_normalized(raw_dir):
    src_dir, dst_dir = raw_dir
    src = src_dir / "test.jsonl"
    src.write_text('{"title":"T","body":"a&nbsp;b","content_type":"picture_book"}\n', encoding="utf-8")
    process_file(src)
    record = json.loads((dst_dir / "test.jsonl").read_text(encoding="utf-8"))
    assert record["body"] == "a b"
    assert "\xa0" not in record["body"]


def test_process_file_skips_blank_lines(raw_dir):
    src_dir, dst_dir = raw_dir
    src = src_dir / "test.jsonl"
    src.write_text(
        '{"title":"A","body":"x","content_type":"picture_book"}\n'
        "\n"
        '{"title":"B","body":"y","content_type":"picture_book"}\n',
        encoding="utf-8",
    )
    process_file(src)
    lines = (dst_dir / "test.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_process_file_malformed_json_raises(raw_dir):
    src_dir, dst_dir = raw_dir
    src = src_dir / "test.jsonl"
    src.write_text(
        '{"title":"A","body":"x","content_type":"picture_book"}\n'
        "NOT_JSON\n",
        encoding="utf-8",
    )
    with pytest.raises(json.JSONDecodeError):
        process_file(src)
    # dst should not exist (tmp file not renamed)
    assert not (dst_dir / "test.jsonl").exists()
