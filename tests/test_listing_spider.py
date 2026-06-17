import jsonschema
from scrapy.http import HtmlResponse, Request

from crawlers.tier1.moc_children.spiders.listing_spider import (
    build_raw_record,
    extract_book_links,
    next_page_url,
    normalize_listing_record,
)
from schemas.validate import load_schema


def _fake_response(url: str, html: str) -> HtmlResponse:
    return HtmlResponse(url=url, body=html.encode("utf-8"), request=Request(url=url))


def test_extract_book_links_finds_animate_class_links():
    html = '<ul><li><a class="animate-item" href="/book/123">故事A</a></li></ul>'
    response = _fake_response("https://children.moc.gov.tw/animate_list", html)
    links = extract_book_links(response)
    assert links == ["https://children.moc.gov.tw/book/123"]


def test_extract_book_links_deduplicates():
    html = (
        '<a class="animate-item" href="/book/1">A</a>'
        '<a class="animate-item" href="/book/1">A again</a>'
    )
    response = _fake_response("https://children.moc.gov.tw/animate_list", html)
    assert len(extract_book_links(response)) == 1


def test_extract_book_links_filters_external_domains():
    html = '<a href="https://evil.com/book">外部連結</a>'
    response = _fake_response("https://children.moc.gov.tw/animate_list", html)
    assert extract_book_links(response) == []


def test_next_page_url_returns_none_when_absent():
    response = _fake_response("https://children.moc.gov.tw/animate_list", "<html></html>")
    assert next_page_url(response) is None


def test_next_page_url_resolves_relative_href():
    html = '<a class="next" href="/animate_list?page=2">下一頁</a>'
    response = _fake_response("https://children.moc.gov.tw/animate_list", html)
    url = next_page_url(response)
    assert url == "https://children.moc.gov.tw/animate_list?page=2"


def test_next_page_url_returns_none_when_href_is_current_page():
    html = '<a class="next" href="/animate_list">下一頁</a>'
    response = _fake_response("https://children.moc.gov.tw/animate_list", html)
    assert next_page_url(response) is None


def test_build_raw_record_extracts_h1_title():
    html = "<h1>小熊的故事</h1><main><p>從前有隻小熊。</p></main>"
    response = _fake_response("https://children.moc.gov.tw/book/1", html)
    raw = build_raw_record(response)
    assert raw["title"] == "小熊的故事"
    assert "從前有隻小熊" in raw["description"]
    assert raw["url"] == "https://children.moc.gov.tw/book/1"


def test_build_raw_record_falls_back_title_as_description_when_no_body():
    html = "<h1>只有標題</h1>"
    response = _fake_response("https://children.moc.gov.tw/book/2", html)
    raw = build_raw_record(response)
    assert raw["description"] == "只有標題"


def test_normalize_listing_record_passes_schema():
    raw = {
        "title": "小熊的故事",
        "description": "從前有隻小熊住在森林裡。",
        "url": "https://children.moc.gov.tw/book/1",
    }
    record = normalize_listing_record(raw, 1)
    jsonschema.validate(record, load_schema(), format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)


def test_normalize_listing_record_sets_id_and_source():
    raw = {"title": "測試", "description": "內文", "url": "https://children.moc.gov.tw/book/42"}
    record = normalize_listing_record(raw, 42)
    assert record["id"] == "MOC-000042"
    assert record["source"] == "MOC_CHILDREN"
    assert record["license_type"] == "ogdl-tw-1"
    assert record["word_count"] == len("內文")
