"""
歌詞萃取 pipeline：讀取 data/raw/moc_song.jsonl，
下載各首兒歌的樂譜 PDF，萃取歌詞文字，原地回填 body 欄位。

背景：song_spider 產出的 body 欄位只有歌曲標題（PDF 萃取保留為後續階段）。
本腳本補齊 body，使 clean → label pipeline 能取得真實歌詞進行聲韻分析。

樂譜 PDF 結構：
  歌詞音節散佈在音符符號（œ ˙ ‰ 等）之間，每個漢字獨立對應一個音符。
  四聲部（SATB）標題列會重複相同字元恰好 4 次（例如「叮叮叮叮」）。

萃取策略：
  1. 保留純漢字 token（U+3400–U+9FFF，含 Extension A），過濾音符符號及 ASCII
  2. 將 4 個以上連續相同字元壓縮為 1（清除 SATB 標題 artifact；合法的 2–3 次重複保留）
  3. 保留 PDF 原始行結構，供下游 analyze_phonics 的 splitlines() 計算重複比
  4. PDF URL 存於 raw_metadata.sheet_music_url 欄位
"""
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pdfplumber

from crawlers.config import DOWNLOAD_DELAY as _DOWNLOAD_DELAY, USER_AGENT as _USER_AGENT

RAW_DIR = Path(__file__).parent.parent / "data/raw"
INPUT_FILE = RAW_DIR / "moc_song.jsonl"

_MAX_RETRIES = 3


def clean_pdf_text(raw_text: str, *, latin_ok: bool = False) -> str:
    """從樂譜 PDF 萃取出的原始文字中清出歌詞，保留行結構供 phonics 分析。

    - 保留純漢字 token（U+3400–U+9FFF，含 CJK Extension A），過濾音符及 ASCII
    - 將 4+ 連續相同字元壓縮為 1（SATB 標題 artifact）；2–3 次重複保留
    - latin_ok=True：同時保留純拉丁字母 token（≥2 字元），供原住民族語羅馬拼音使用
    - 行結構以 \\n 分隔，供 label.py analyze_phonics 的 splitlines() 使用
    """
    lines = []
    for line in raw_text.splitlines():
        line_tokens = []
        for token in line.split():
            if re.fullmatch(r"[㐀-鿿]+", token):
                cleaned = re.sub(r"(.)\1{3,}", r"\1", token)
                line_tokens.append(cleaned)
            elif latin_ok and re.fullmatch(r"[A-Za-z']{2,}", token):
                line_tokens.append(token)
        if line_tokens:
            sep = " " if latin_ok else ""
            lines.append(sep.join(line_tokens))
    return "\n".join(lines)


def extract_lyrics_from_pdf(pdf_bytes: bytes, *, latin_ok: bool = False) -> str:
    """用 pdfplumber 從已下載的 PDF bytes 萃取全文，再呼叫 clean_pdf_text 清出歌詞。"""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return clean_pdf_text("\n".join(pages), latin_ok=latin_ok)


def _fetch_pdf(url: str) -> bytes:
    """Fetch PDF bytes from url with up to _MAX_RETRIES attempts.

    Linear backoff: _DOWNLOAD_DELAY * attempt seconds. HTTP 4xx is non-retriable
    and raises immediately; 5xx and network errors are retried.
    """
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise  # 4xx: non-retriable
            if attempt == _MAX_RETRIES:
                raise
            print(f"    retry {attempt}/{_MAX_RETRIES}: {exc}", file=sys.stderr)
        except Exception as exc:
            if attempt == _MAX_RETRIES:
                raise
            print(f"    retry {attempt}/{_MAX_RETRIES}: {exc}", file=sys.stderr)
        time.sleep(_DOWNLOAD_DELAY * attempt)
    raise RuntimeError("unreachable")  # pragma: no cover


def process_file(input_path: Path) -> int:
    """讀取 moc_song.jsonl，下載 PDF 萃取歌詞，原地回填 body/word_count。

    Returns number of records that failed PDF extraction (0 = all OK).
    """
    if not input_path.exists():
        print(
            f"ERROR: {input_path} not found. Run 'make crawl-moc-song' first.",
            file=sys.stderr,
        )
        raise FileNotFoundError(str(input_path))

    records = []
    with input_path.open(encoding="utf-8") as fin:
        for line in fin:
            if line.strip():
                records.append(json.loads(line))

    print(f"Processing {len(records)} records from {input_path}")

    failures = 0
    tmp = input_path.with_suffix(".tmp")
    try:
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
                    lang = (entry.get("language") or [""])[0]
                    lyrics = extract_lyrics_from_pdf(pdf_bytes, latin_ok=(lang == "indigenous"))
                    if lyrics:
                        entry["body"] = lyrics
                        entry["word_count"] = len(lyrics)
                        print(f"    -> {len(lyrics)} chars")
                    else:
                        print(
                            "    -> WARNING: PDF yielded 0 lyrics, body unchanged",
                            file=sys.stderr,
                        )
                        failures += 1
                except Exception as exc:
                    print(
                        f"    -> ERROR: {exc}, keeping original body",
                        file=sys.stderr,
                    )
                    failures += 1

                fout.write(json.dumps(entry, ensure_ascii=False) + "\n")

                if i < len(records) - 1:
                    time.sleep(_DOWNLOAD_DELAY)

        tmp.replace(input_path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    if failures:
        print(
            f"\nWARNING: {failures}/{len(records)} records failed PDF extraction.",
            file=sys.stderr,
        )
    print(f"Done: {input_path}")
    return failures


if __name__ == "__main__":
    failed = process_file(INPUT_FILE)
    if failed:
        sys.exit(1)
