"""
歌詞萃取 pipeline：讀取 data/raw/moc_song.jsonl，
下載各首兒歌的樂譜 PDF，萃取歌詞文字，原地回填 body 欄位。

背景：song_spider 產出的 body 欄位只有歌曲標題（PDF 萃取保留為後續階段）。
本腳本補齊 body，使 clean → label pipeline 能取得真實歌詞進行聲韻分析。

樂譜 PDF 結構：
  歌詞音節散佈在音符符號（œ ˙ ‰ 等）之間，每個漢字獨立對應一個音符。
  四聲部（SATB）標題列會重複相同字元 4 次（例如「叮叮叮叮」）。

萃取策略：
  1. 保留純漢字 token（過濾音符符號、ASCII 字元、標點）
  2. 將 3 個以上連續相同字元壓縮為 1（清除四聲部標題重複 artifact）
"""
import io
import json
import re
import time
import urllib.request
from pathlib import Path

import pdfplumber

RAW_DIR = Path("data/raw")
INPUT_FILE = RAW_DIR / "moc_song.jsonl"

_USER_AGENT = "TCCN-Corpus-Bot/1.0 (+https://github.com/heyu-ai/TCCN-Corpus)"
_DOWNLOAD_DELAY = 2.0
_MAX_RETRIES = 3


def clean_pdf_text(raw_text: str) -> str:
    """
    從樂譜 PDF 萃取出的原始文字中清出歌詞。

    - 保留純漢字 token（U+4E00–U+9FFF），過濾音符符號及 ASCII
    - 將 3 個以上連續相同字元壓縮為 1（四聲部標題 artifact）
    """
    tokens = []
    for line in raw_text.splitlines():
        for token in line.split():
            if re.fullmatch(r"[一-鿿]+", token):
                cleaned = re.sub(r"(.)\1{2,}", r"\1", token)
                tokens.append(cleaned)
    return "".join(tokens)


def extract_lyrics_from_pdf(pdf_bytes: bytes) -> str:
    """下載並用 pdfplumber 萃取 PDF 全文，再呼叫 clean_pdf_text 清出歌詞。"""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return clean_pdf_text("\n".join(pages))


def _fetch_pdf(url: str) -> bytes:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as exc:
            if attempt == _MAX_RETRIES:
                raise
            print(f"    retry {attempt}/{_MAX_RETRIES}: {exc}")
            time.sleep(_DOWNLOAD_DELAY * attempt)
    raise RuntimeError("unreachable")  # pragma: no cover


def process_file(input_path: Path) -> None:
    """讀取 moc_song.jsonl，下載 PDF 萃取歌詞，原地回填 body/word_count。"""
    records = []
    with input_path.open(encoding="utf-8") as fin:
        for line in fin:
            if line.strip():
                records.append(json.loads(line))

    print(f"Processing {len(records)} records from {input_path}")

    tmp = input_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fout:
        for i, entry in enumerate(records):
            pdf_url = entry.get("raw_metadata", {}).get("sheet_music_url", "")
            title = entry.get("title", "?")

            if not pdf_url:
                print(f"  [{i + 1}/{len(records)}] {title}: no PDF URL, skip")
                fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
                continue

            try:
                print(f"  [{i + 1}/{len(records)}] {title}: {pdf_url}")
                pdf_bytes = _fetch_pdf(pdf_url)
                lyrics = extract_lyrics_from_pdf(pdf_bytes)
                if lyrics:
                    entry["body"] = lyrics
                    entry["word_count"] = len(lyrics)
                print(f"    -> {len(lyrics)} chars")
            except Exception as exc:
                print(f"    -> ERROR: {exc}, keeping original body")

            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

            if i < len(records) - 1:
                time.sleep(_DOWNLOAD_DELAY)

    tmp.rename(input_path)
    print(f"Done: {input_path}")


if __name__ == "__main__":
    process_file(INPUT_FILE)
