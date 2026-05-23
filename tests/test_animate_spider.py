import json

from crawlers.tier1.moc_children.spiders.animate_spider import iter_seed_entries


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
