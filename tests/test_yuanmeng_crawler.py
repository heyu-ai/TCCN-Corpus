from urllib.parse import urljoin

import jsonschema

from schemas.validate import load_schema

from crawlers.tier1.yuanmeng.yuanmeng_crawler import (
    BASE_URL,
    build_dry_run_payload,
    filter_book_links,
    filter_pagination,
    map_language,
    normalize_book_record,
    parse_age_range,
    parse_book_id,
)


def test_filter_book_links_keeps_book_hrefs():
    anchors = [
        {"href": "/books/123", "text": "故事A"},
        {"href": "/about", "text": "關於我們"},
        {"href": "/all-books", "text": "全部書籍"},
        {"href": "/contact", "text": "聯絡"},
    ]
    result = filter_book_links(anchors)
    hrefs = {r["href"] for r in result}
    assert "/books/123" in hrefs
    assert "/all-books" in hrefs
    assert "/about" not in hrefs


def test_filter_book_links_caps_at_twenty():
    anchors = [{"href": f"/books/{i}", "text": f"故事{i}"} for i in range(30)]
    result = filter_book_links(anchors)
    assert len(result) == 20


def test_filter_pagination_finds_chinese_and_english_next():
    nodes = [
        {"text": "下一頁", "href": "/?page=2"},
        {"text": "首頁", "href": "/"},
        {"text": "Next", "href": "/?page=3"},
        {"text": "無關連結", "href": "/about"},
    ]
    result = filter_pagination(nodes)
    texts = {r["text"] for r in result}
    assert "下一頁" in texts
    assert "Next" in texts
    assert "首頁" not in texts
    assert "無關連結" not in texts


def test_build_dry_run_payload_structure():
    book_links = [{"href": "/books/1", "text": "故事A"}]
    payload = build_dry_run_payload(BASE_URL, "圓夢繪本", book_links, [])
    assert payload["base_url"] == BASE_URL
    assert payload["title"] == "圓夢繪本"
    assert payload["book_link_count"] == 1
    assert payload["book_links"][0]["text"] == "故事A"
    assert payload["book_links"][0]["url"] == urljoin(BASE_URL, "/books/1")
    assert payload["pagination_candidates"] == []


def test_build_dry_run_payload_resolves_relative_urls():
    book_links = [{"href": "books/2", "text": "故事B"}]
    payload = build_dry_run_payload("https://storybook.nlpi.edu.tw/", "T", book_links, [])
    assert payload["book_links"][0]["url"].startswith("https://storybook.nlpi.edu.tw/")


def test_filter_pagination_matches_href_page_pattern():
    nodes = [
        {"text": "1", "href": "/list?page=1"},
        {"text": "2", "href": "/list?page=2"},
        {"text": "關於", "href": "/about"},
    ]
    result = filter_pagination(nodes)
    hrefs = {r["href"] for r in result}
    assert "/list?page=1" in hrefs
    assert "/list?page=2" in hrefs
    assert "/about" not in hrefs


# --- Phase 3: metadata pure-function tests ---

def test_parse_book_id_extracts_number():
    assert parse_book_id("openWindow('playbook2.aspx?NO=125')") == "125"


def test_parse_book_id_returns_none_when_absent():
    assert parse_book_id("") is None
    assert parse_book_id("openWindow('about.aspx')") is None


def test_map_language_mandarin():
    assert map_language("中文") == "zh-TW"
    assert map_language("中文+拼注音") == "zh-TW"


def test_map_language_taiwanese():
    assert map_language("台語") == "nan-TW"
    assert map_language("臺語版") == "nan-TW"


def test_map_language_hakka():
    assert map_language("客語") == "hak-TW"


def test_map_language_english():
    assert map_language("英文") == "en"


def test_map_language_defaults_to_zh_tw():
    assert map_language("") == "zh-TW"
    assert map_language("不知道") == "zh-TW"


def test_parse_age_range_standard():
    assert parse_age_range("7-9歲") == {"min": 7, "max": 9}
    assert parse_age_range("10-12歲") == {"min": 10, "max": 12}
    assert parse_age_range("0-3歲") == {"min": 0, "max": 3}


def test_parse_age_range_defaults_when_empty():
    assert parse_age_range("") == {"min": 0, "max": 12}
    assert parse_age_range("適讀年齡不明") == {"min": 0, "max": 12}


def test_normalize_book_record_passes_schema():
    card = {
        "title": "小紅帽的故事",
        "author": "某作者",
        "language": "中文+拼注音",
        "onclick": "openWindow('playbook2.aspx?NO=125')",
        "age_text": "7-9歲",
    }
    record = normalize_book_record(card, 1)
    assert record is not None
    jsonschema.validate(record, load_schema(), format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)
    assert record["content_type"] == "picture_book"
    assert record["license_type"] == "research-only"
    assert record["language"] == ["zh-TW"]
    assert record["age_range"] == {"min": 7, "max": 9}
    assert record["raw_metadata"]["book_id"] == "125"


def test_normalize_book_record_returns_none_without_book_id():
    card = {"title": "無ID書", "onclick": "openWindow('about.aspx')"}
    assert normalize_book_record(card, 1) is None
