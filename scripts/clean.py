"""
清洗 pipeline：讀取 data/raw/*.jsonl，輸出至 data/cleaned/
"""
import json
import re
from pathlib import Path

RAW_DIR = Path("data/raw")
CLEANED_DIR = Path("data/cleaned")
CLEANED_DIR.mkdir(parents=True, exist_ok=True)


def clean_body(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def process_file(src: Path):
    dst = CLEANED_DIR / src.name
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            entry = json.loads(line)
            entry["body"] = clean_body(entry.get("body", ""))
            entry["word_count"] = len(entry["body"])
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"cleaned: {src.name} → {dst}")


if __name__ == "__main__":
    for f in RAW_DIR.glob("*.jsonl"):
        process_file(f)
