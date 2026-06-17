from urllib.parse import urljoin

from crawlers.tier1.yuanmeng.yuanmeng_crawler import (
    BASE_URL,
    build_dry_run_payload,
    filter_book_links,
    filter_pagination,
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
