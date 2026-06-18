"""
清洗 pipeline：讀取 data/raw/*.jsonl，輸出至 data/cleaned/

處理步驟：
1. HTML entity decode (&amp; → &)，NBSP（U+00A0）正規化為一般空格
2. 全形 ASCII → 半形（！→! 等）
3. 移除 C0 控制字元（保留 TAB/LF/CR）及 DEL（U+007F）
4. 連續空白（3 個以上）壓縮為 \\n\\n
5. 補上 cleaned_at 時間戳
"""
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")

# Full-width ASCII U+FF01..U+FF5E → half-width U+0021..U+007E
_FULLWIDTH_TABLE = str.maketrans(
    "".join(chr(0xFF01 + i) for i in range(94)),
    "".join(chr(0x21 + i) for i in range(94)),
)
_FULLWIDTH_TABLE[ord("　")] = ord(" ")  # ideographic space → regular space


def normalize_fullwidth(text: str) -> str:
    """Convert full-width ASCII characters and ideographic space to half-width."""
    return text.translate(_FULLWIDTH_TABLE)


def clean_body(text: str) -> str:
    """Decode HTML entities (NBSP normalized to space), normalize full-width, strip C0/DEL
    control chars, collapse 3+ consecutive whitespace to double-newline."""
    text = html.unescape(text)
    text = text.replace("\xa0", " ")  # normalize NBSP before whitespace collapse
    text = normalize_fullwidth(text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def process_file(src: Path) -> None:
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    dst = CLEANED_DIR / src.name
    dst_tmp = dst.with_suffix(".tmp")
    now = datetime.now(timezone.utc).isoformat()
    with src.open(encoding="utf-8") as fin, dst_tmp.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            entry = json.loads(line)
            entry["body"] = clean_body(entry.get("body", ""))
            entry["word_count"] = len(entry["body"])
            entry["cleaned_at"] = now
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
    dst_tmp.rename(dst)
    print(f"cleaned: {src.name} -> {dst}")


if __name__ == "__main__":
    for f in RAW_DIR.glob("*.jsonl"):
        process_file(f)
