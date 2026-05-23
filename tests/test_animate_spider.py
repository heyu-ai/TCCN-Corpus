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
