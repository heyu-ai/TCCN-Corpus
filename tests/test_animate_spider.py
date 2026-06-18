import json

from crawlers.tier1.moc_children.spiders.animate_spider import (
    AnimateSpider,
    is_allowed_source_url,
    iter_seed_entries,
)


def test_iter_seed_entries_streams_jsonl(tmp_path):
    seed_path = tmp_path / "seed.jsonl"
    seed_path.write_text(
        "\n".join(
            [
                json.dumps({"title": "第一筆"}, ensure_ascii=False),
                "",
                json.dumps({"title": "第二筆"}, ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )

    seeds = iter_seed_entries(seed_path)

    assert next(seeds)["title"] == "第一筆"
    assert next(seeds)["title"] == "第二筆"


def test_iter_seed_entries_skips_invalid_lines(tmp_path):
    seed_path = tmp_path / "seed.jsonl"
    seed_path.write_text(
        "\n".join(
            [
                json.dumps({"title": "有效"}, ensure_ascii=False),
                "not-json",
                json.dumps(["not-dict"], ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )
    seeds = list(iter_seed_entries(seed_path))
    assert len(seeds) == 1
    assert seeds[0]["title"] == "有效"


def test_is_allowed_source_url():
    assert is_allowed_source_url("https://children.moc.gov.tw/animate_list")
    assert not is_allowed_source_url("https://example.com/path")


def test_start_requests_fallbacks_to_default_for_external_url(tmp_path):
    seed_path = tmp_path / "seed.jsonl"
    seed_path.write_text(
        json.dumps({"title": "測試", "source_url": "https://example.com/evil"}, ensure_ascii=False),
        encoding="utf-8",
    )
    spider = AnimateSpider(seed_file=str(seed_path))
    req = next(spider.start_requests())
    assert req.url == "https://children.moc.gov.tw/animate_list"


def test_parse_detail_extracts_title_from_h1(fake_response):
    seed = {"id": "MOC-000001", "title": "種子標題", "body": "種子內文"}
    html = "<h1>頁面標題</h1><main><p>頁面段落內文。</p></main>"
    spider = AnimateSpider.__new__(AnimateSpider)
    response = fake_response("https://children.moc.gov.tw/book/1", html)
    result = list(spider.parse_detail(response, seed=seed))
    assert len(result) == 1
    assert result[0]["title"] == "頁面標題"


def test_parse_detail_falls_back_to_seed_title_when_page_has_none(fake_response):
    seed = {"id": "MOC-000002", "title": "種子標題", "body": "種子內文"}
    html = "<div>無 h1/h2 標題</div>"
    spider = AnimateSpider.__new__(AnimateSpider)
    response = fake_response("https://children.moc.gov.tw/book/2", html)
    result = list(spider.parse_detail(response, seed=seed))
    assert result[0]["title"] == "種子標題"
    assert result[0]["body"] == "種子內文"


def test_parse_detail_extracts_body_from_main_paragraphs(fake_response):
    seed = {"id": "MOC-000003", "title": "T", "body": ""}
    html = "<main><p>第一段。</p><p>第二段。</p></main>"
    spider = AnimateSpider.__new__(AnimateSpider)
    response = fake_response("https://children.moc.gov.tw/book/3", html)
    result = list(spider.parse_detail(response, seed=seed))
    assert "第一段" in result[0]["body"]
    assert "第二段" in result[0]["body"]
    assert result[0]["word_count"] == len(result[0]["body"])
