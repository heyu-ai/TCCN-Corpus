import jsonschema
from schemas.validate import load_schema

from crawlers.tier1.moc_children.spiders.song_spider import (
    extract_metadata,
    extract_song_links,
    infer_language_from_meta,
    next_page_url,
    normalize_song_record,
)


def test_extract_song_links_finds_song_hrefs(fake_response):
    html = (
        '<a href="/song/479"><img alt="讓愛看得的見"></a>'
        '<h3>讓愛看得的見</h3>'
        '<a href="/song/478"><img alt="幸福一家人"></a>'
        '<h3>幸福一家人</h3>'
    )
    response = fake_response("https://children.moc.gov.tw/song_list", html)
    links = extract_song_links(response)
    assert "https://children.moc.gov.tw/song/479" in links
    assert "https://children.moc.gov.tw/song/478" in links


def test_extract_song_links_deduplicates(fake_response):
    html = (
        '<a href="/song/1">A</a>'
        '<a href="/song/1">A again</a>'
    )
    response = fake_response("https://children.moc.gov.tw/song_list", html)
    assert len(extract_song_links(response)) == 1


def test_extract_song_links_ignores_external(fake_response):
    html = '<a href="https://evil.com/song/1">外部</a>'
    response = fake_response("https://children.moc.gov.tw/song_list", html)
    assert extract_song_links(response) == []


def test_next_page_url_returns_none_when_absent(fake_response):
    response = fake_response("https://children.moc.gov.tw/song_list", "<html></html>")
    assert next_page_url(response) is None


def test_next_page_url_returns_none_for_self_loop(fake_response):
    # 最後一頁的「下一頁」指向自身，應返回 None 防止無窮迴圈
    html = '<a href="/song_list?language=1&page=3">下一頁</a>'
    response = fake_response("https://children.moc.gov.tw/song_list?language=1&page=3", html)
    assert next_page_url(response) is None


def test_next_page_url_resolves_chinese_next(fake_response):
    html = '<a href="/song_list?language=1&page=2">下一頁</a>'
    response = fake_response("https://children.moc.gov.tw/song_list?language=1", html)
    url = next_page_url(response)
    assert url == "https://children.moc.gov.tw/song_list?language=1&page=2"


def _meta_ul(*items: tuple[str, str]) -> str:
    """Helper: build MOC-style metadata ul from (field, value) pairs.

    Real page structure:
      <h2>歌名</h2>
      <ul class="list-unstyled">
        <li><span>類別</span><span>：</span>\n  華語\n</li>
        ...
      </ul>
    """
    lis = "".join(
        f'<li><span>{field}</span><span>：</span>\n  {value}\n</li>'
        for field, value in items
    )
    return f'<ul class="list-unstyled">{lis}</ul>'


def test_extract_metadata_parses_moc_detail(fake_response):
    html = (
        "<h2>讓愛看得的見</h2>"
        + _meta_ul(("類別", "華語"), ("作曲", "王溪泉、賴家慶"), ("作詞", "洪順齊"), ("演唱", "周予柔"))
    )
    response = fake_response("https://children.moc.gov.tw/song/479", html)
    meta = extract_metadata(response)
    assert meta["composer"] == "王溪泉、賴家慶"
    assert meta["lyricist"] == "洪順齊"
    assert meta["singer"] == "周予柔"
    assert meta["category"] == "華語"


def test_infer_language_from_meta_mandarin(fake_response):
    html = "<h2>X</h2>" + _meta_ul(("類別", "華語"))
    response = fake_response("https://children.moc.gov.tw/song/1", html)
    assert infer_language_from_meta(response) == "zh-TW"


def test_infer_language_from_meta_taiwanese(fake_response):
    html = "<h2>X</h2>" + _meta_ul(("類別", "臺灣台語"))
    response = fake_response("https://children.moc.gov.tw/song/2", html)
    assert infer_language_from_meta(response) == "nan-TW"


def test_infer_language_from_meta_hakka(fake_response):
    html = "<h2>X</h2>" + _meta_ul(("類別", "客語"))
    response = fake_response("https://children.moc.gov.tw/song/3", html)
    assert infer_language_from_meta(response) == "hak-TW"


def test_infer_language_from_meta_indigenous(fake_response):
    html = "<h2>X</h2>" + _meta_ul(("類別", "原住民族語"))
    response = fake_response("https://children.moc.gov.tw/song/4", html)
    assert infer_language_from_meta(response) == "indigenous"


def test_infer_language_returns_none_when_no_category(fake_response):
    html = "<h2>X</h2>" + _meta_ul(("作曲", "某人"))
    response = fake_response("https://children.moc.gov.tw/song/5", html)
    assert infer_language_from_meta(response) is None


def test_infer_language_returns_none_for_unknown_category(fake_response):
    # 類別值不在 _LANG_MAP 中（如英語）應返回 None，讓 parse_detail 使用種子語言 fallback
    html = "<h2>X</h2>" + _meta_ul(("類別", "英語"))
    response = fake_response("https://children.moc.gov.tw/song/6", html)
    assert infer_language_from_meta(response) is None


def test_normalize_song_record_passes_schema(fake_response):
    html = (
        "<h2>雨的花蕊</h2>"
        + _meta_ul(("類別", "臺灣台語"), ("作詞", "某詞人"))
        + '<a href="https://children.moc.gov.tw/resource/song_pdf/475.pdf">曲譜下載</a>'
    )
    response = fake_response("https://children.moc.gov.tw/song/475", html)
    meta = extract_metadata(response)
    lang = infer_language_from_meta(response)
    record = normalize_song_record(response, lang, meta, 1)
    jsonschema.validate(record, load_schema(), format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER)
    assert record["content_type"] == "nursery_rhyme"
    assert record["language"] == ["nan-TW"]
    assert record["has_audio"] is True
    assert record["raw_metadata"]["sheet_music_url"].endswith("475.pdf")
