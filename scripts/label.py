"""
標籤化 pipeline：讀取 data/cleaned/*.jsonl，輸出至 data/labeled/
依字數與詞彙複雜度自動推算 age_range，需人工複審後上線。
"""
import json
from pathlib import Path

CLEANED_DIR = Path("data/cleaned")
LABELED_DIR = Path("data/labeled")
LABELED_DIR.mkdir(parents=True, exist_ok=True)

# 字數 → 適讀年齡粗估規則（需依實際語料校正）
AGE_RULES = [
    (150,  {"min": 0, "max": 3}),
    (400,  {"min": 2, "max": 4}),
    (800,  {"min": 4, "max": 6}),
    (1500, {"min": 5, "max": 8}),
]


def infer_age_range(word_count: int) -> dict:
    for threshold, age in AGE_RULES:
        if word_count <= threshold:
            return age
    return {"min": 6, "max": 12}


def process_file(src: Path):
    dst = LABELED_DIR / src.name
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            entry = json.loads(line)
            if not entry.get("age_range"):
                entry["age_range"] = infer_age_range(entry.get("word_count", 0))
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"labeled: {src.name} → {dst}")


if __name__ == "__main__":
    for f in CLEANED_DIR.glob("*.jsonl"):
        process_file(f)
