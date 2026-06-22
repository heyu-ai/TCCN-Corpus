import json

import pytest

from scripts.extract_song_lyrics import clean_pdf_text, extract_lyrics_from_pdf, process_file


# --- clean_pdf_text ---

def test_collapses_four_char_repeat():
    # SATB 標題列：同字元出現 4 次 → 壓縮為 1
    assert clean_pdf_text("叮叮叮叮 噹噹噹噹") == "叮噹"


def test_preserves_two_char_repeat():
    # 歌詞中合法的 2 音節重複（叮叮）不應被壓縮
    assert clean_pdf_text("叮叮") == "叮叮"


def test_preserves_three_char_repeat():
    # 3-repeat 是合法疊聲詞，不應壓縮（SATB artifact 是嚴格的 4-repeat）
    assert clean_pdf_text("叮叮叮") == "叮叮叮"


def test_filters_notation_symbols():
    # 音符符號（非漢字）應被過濾
    assert clean_pdf_text("& c œ œ œ ˙ ‰") == ""


def test_latin_ok_preserves_indigenous_words():
    # 原住民族語 PDF 為羅馬拼音，latin_ok=True 時保留純拉丁 token
    result = clean_pdf_text("Duduli ko wawa 叮噹", latin_ok=True)
    assert "Duduli" in result
    assert "wawa" in result
    assert "叮噹" in result


def test_latin_ok_filters_single_chars_and_symbols():
    # 單字母（PDF 雜訊）和音符不應被保留
    assert clean_pdf_text("c f p œ ˙ AB Wawa", latin_ok=True) == "AB Wawa"


def test_latin_ok_false_filters_latin_by_default():
    # 預設行為：不開 latin_ok 時拉丁字母仍被過濾
    assert clean_pdf_text("Duduli ko wawa") == ""


def test_filters_ascii_digits():
    # 小節號碼（純數字）應被過濾
    assert clean_pdf_text("5\n叮叮\n9") == "叮叮"


def test_filters_ascii_text():
    # MIDI 等英文 token 應被過濾
    assert clean_pdf_text("MIDI 02 叮噹") == "叮噹"


def test_extracts_lyrics_from_mixed_line():
    # 真實場景：歌詞與音符混合排列（空格分隔）
    line = "叮 叮 噹 噹 窗 外 風 鈴 響 我 知 道 風 來 了"
    result = clean_pdf_text(line)
    assert "叮" in result
    assert "窗" in result
    assert "了" in result
    assert len(result) == 15


def test_empty_input():
    assert clean_pdf_text("") == ""


def test_whitespace_only_input():
    assert clean_pdf_text("   \n\t  ") == ""


def test_full_satb_header_pattern():
    # 模擬四聲部標題：標題字元重複 4 次，credits 重複 4 次
    # 行結構保留，兩行以 \n 分隔
    header = "叮叮叮叮 噹噹噹噹 叮叮叮叮 咚咚咚咚\n作作作作 陳陳陳陳陳陳陳陳陳陳陳陳"
    result = clean_pdf_text(header)
    assert result == "叮噹叮咚\n作陳"


def test_lyrics_section_after_header():
    # 標題後的歌詞行：每字一個 token，空格分隔
    text = "叮叮叮叮 噹噹噹噹\n叮 叮 噹 噹 窗 外 風 鈴 響"
    result = clean_pdf_text(text)
    assert result.startswith("叮噹")
    assert "窗" in result
    assert "響" in result


# --- extract_lyrics_from_pdf (integration with real PDF bytes) ---

def _make_minimal_pdf(text: str) -> bytes:
    """建立最小 valid PDF，文字內容為 text（UTF-8 encoded in stream）。"""
    import zlib

    # 用 pdfplumber 能讀取的最小 PDF 結構
    # 這裡用純 ASCII stream，只測 pdfplumber 能讀到文字
    content_stream = f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET".encode()
    stream_data = zlib.compress(content_stream)
    stream_len = len(stream_data)

    # 非常精簡的 PDF（不含字型定義，pdfplumber 可能拿不到文字，但不會崩潰）
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Contents 4 0 R >>\nendobj\n"
        + f"4 0 obj\n<< /Length {stream_len} /Filter /FlateDecode >>\nstream\n".encode()
        + stream_data
        + b"\nendstream\nendobj\n"
        b"xref\n0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000206 00000 n \n"
        b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n"
        + str(206 + stream_len + 20).encode()
        + b"\n%%EOF"
    )
    return pdf


def test_extract_lyrics_from_pdf_does_not_crash():
    # pdfplumber 能處理 bytes 輸入且不崩潰（即使萃取結果為空）
    pdf_bytes = _make_minimal_pdf("test")
    result = extract_lyrics_from_pdf(pdf_bytes)
    assert isinstance(result, str)


# --- process_file integration ---

@pytest.fixture()
def song_dir(tmp_path):
    return tmp_path / "moc_song.jsonl"


def test_process_file_no_pdf_url(song_dir, monkeypatch):
    record = {
        "id": "MOC-abc",
        "title": "測試曲",
        "body": "測試曲",
        "word_count": 3,
        "raw_metadata": {"sheet_music_url": ""},
    }
    song_dir.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    process_file(song_dir)

    out = json.loads(song_dir.read_text(encoding="utf-8"))
    assert out["body"] == "測試曲"
    assert out["word_count"] == 3


def test_process_file_updates_body_and_word_count(song_dir, monkeypatch):
    record = {
        "id": "MOC-abc",
        "title": "測試曲",
        "body": "測試曲",
        "word_count": 3,
        "raw_metadata": {"sheet_music_url": "https://example.com/song.pdf"},
    }
    song_dir.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    def fake_fetch(url: str) -> bytes:
        return _make_minimal_pdf("test")

    def fake_extract(pdf_bytes: bytes, *, latin_ok: bool = False) -> str:
        return "叮噹叮咚窗外風鈴響"

    monkeypatch.setattr("scripts.extract_song_lyrics._fetch_pdf", fake_fetch)
    monkeypatch.setattr("scripts.extract_song_lyrics.extract_lyrics_from_pdf", fake_extract)
    monkeypatch.setattr("scripts.extract_song_lyrics._DOWNLOAD_DELAY", 0)

    process_file(song_dir)

    out = json.loads(song_dir.read_text(encoding="utf-8"))
    assert out["body"] == "叮噹叮咚窗外風鈴響"
    assert out["word_count"] == 9


def test_process_file_fetch_error_keeps_original(song_dir, monkeypatch):
    record = {
        "id": "MOC-abc",
        "title": "測試曲",
        "body": "測試曲",
        "word_count": 3,
        "raw_metadata": {"sheet_music_url": "https://example.com/song.pdf"},
    }
    song_dir.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    def fake_fetch(url: str) -> bytes:
        raise ConnectionError("network error")

    monkeypatch.setattr("scripts.extract_song_lyrics._fetch_pdf", fake_fetch)
    monkeypatch.setattr("scripts.extract_song_lyrics._MAX_RETRIES", 1)
    monkeypatch.setattr("scripts.extract_song_lyrics._DOWNLOAD_DELAY", 0)

    process_file(song_dir)

    out = json.loads(song_dir.read_text(encoding="utf-8"))
    assert out["body"] == "測試曲"


def test_process_file_empty_lyrics_keeps_original(song_dir, monkeypatch):
    record = {
        "id": "MOC-abc",
        "title": "測試曲",
        "body": "測試曲",
        "word_count": 3,
        "raw_metadata": {"sheet_music_url": "https://example.com/song.pdf"},
    }
    song_dir.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    def fake_fetch(url: str) -> bytes:
        return _make_minimal_pdf("test")

    def fake_extract_empty(pdf_bytes: bytes, *, latin_ok: bool = False) -> str:
        return ""

    monkeypatch.setattr("scripts.extract_song_lyrics._fetch_pdf", fake_fetch)
    monkeypatch.setattr("scripts.extract_song_lyrics.extract_lyrics_from_pdf", fake_extract_empty)
    monkeypatch.setattr("scripts.extract_song_lyrics._DOWNLOAD_DELAY", 0)

    result = process_file(song_dir)

    out = json.loads(song_dir.read_text(encoding="utf-8"))
    assert out["body"] == "測試曲"
    assert out["word_count"] == 3
    assert result == 1  # empty-lyrics counts as failure


def test_process_file_skips_blank_lines(song_dir, monkeypatch):
    r1 = {"id": "MOC-1", "title": "A", "body": "A", "word_count": 1, "raw_metadata": {"sheet_music_url": ""}}
    r2 = {"id": "MOC-2", "title": "B", "body": "B", "word_count": 1, "raw_metadata": {"sheet_music_url": ""}}
    song_dir.write_text(
        json.dumps(r1, ensure_ascii=False) + "\n\n" + json.dumps(r2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.extract_song_lyrics._DOWNLOAD_DELAY", 0)
    process_file(song_dir)
    lines = [ln for ln in song_dir.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
