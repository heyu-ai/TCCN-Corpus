"""
標籤化 pipeline：讀取 data/cleaned/*.jsonl，輸出至 data/labeled/

自動填充 schema 欄位：
- developmental_milestone: age_range 與 0-6 歲語言里程碑的重疊帶
- action_cues: 兒歌動作指令關鍵字（nursery_rhyme only）
- phonics.repetition_ratio: 重複行比例（nursery_rhyme，body >= 2 行時）
- themes: 主題關鍵字分類（動物/自然/家庭/友誼/身體認知/情緒）
- labeled_at: 標籤時間戳

注意：age_range 若缺漏則依字數推算（粗估，需人工複審）。
"""
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CLEANED_DIR = Path("data/cleaned")
LABELED_DIR = Path("data/labeled")

_MILESTONE_BANDS = [
    (0, 1, "language_0_1"),
    (1, 2, "language_1_2"),
    (2, 3, "language_2_3"),
    (3, 4, "language_3_4"),
    (4, 5, "language_4_5"),
    (5, 6, "language_5_6"),
]

_ACTION_CUES = [
    (r"拍[拍手]", "拍手"),
    (r"跺腳|踏腳|跺步", "跺腳"),
    (r"轉圈|旋轉|打轉", "轉圈"),
    (r"搖[擺頭]", "搖擺"),
    (r"跳[起躍舞]", "跳躍"),
    (r"點頭", "點頭"),
    (r"揮手", "揮手"),
    (r"踏步|走走", "踏步"),
]

_THEME_KEYWORDS: dict[str, list[str]] = {
    "動物": ["動物", "小狗", "小貓", "兔子", "鳥", "魚", "蝴蝶", "小雞", "牛", "豬", "羊", "熊", "獅子", "老虎", "大象", "猴子", "青蛙"],
    "自然": ["花", "草", "樹", "山", "海", "河", "天空", "雲", "太陽", "月亮", "星星", "雨", "風", "雪"],
    "家庭": ["爸爸", "媽媽", "爺爺", "奶奶", "阿公", "阿嬤", "弟弟", "妹妹", "哥哥", "姊姊"],
    "友誼": ["朋友", "一起", "分享", "幫助", "合作"],
    "身體認知": ["眼睛", "耳朵", "鼻子", "嘴巴", "手腳", "頭", "肚子"],
    "情緒": ["快樂", "開心", "傷心", "生氣", "難過", "興奮"],
}

# 字數 → 適讀年齡粗估規則（閾值需依實際語料校正，需人工複審）
# word_count > 1500 falls through to infer_age_range fallback {"min": 6, "max": 12}
AGE_RULES = [
    (150, {"min": 0, "max": 3}),
    (400, {"min": 2, "max": 4}),
    (800, {"min": 4, "max": 6}),
    (1500, {"min": 5, "max": 8}),
]


def infer_developmental_milestones(age_range: dict) -> list:
    """Return language milestone tags that overlap with the given age_range."""
    lo = age_range.get("min", 0)
    hi = age_range.get("max", 12)
    return [
        ms for (band_lo, band_hi, ms) in _MILESTONE_BANDS
        if band_lo < hi and band_hi > lo
    ]


def detect_action_cues(body: str, content_type: str) -> list:
    """Match physical action keywords; only for nursery_rhyme content."""
    if content_type != "nursery_rhyme":
        return []
    cues: list = []
    seen: set = set()  # guard against future duplicate cue_names in _ACTION_CUES
    for pattern, cue_name in _ACTION_CUES:
        if cue_name not in seen and re.search(pattern, body):
            cues.append(cue_name)
            seen.add(cue_name)
    return cues


def analyze_phonics(body: str, content_type: str) -> dict:
    """Compute repetition_ratio for nursery_rhyme with >= 2 non-empty lines."""
    if content_type != "nursery_rhyme" or not body:
        return {}
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if len(lines) < 2:
        return {}
    counts = Counter(lines)
    repeated = sum(c for c in counts.values() if c > 1)
    return {"repetition_ratio": round(repeated / len(lines), 2)}


def detect_themes(body: str, title: str) -> list:
    """Keyword-based theme classification from combined title and body text."""
    text = title + " " + body
    return [
        theme for theme, keywords in _THEME_KEYWORDS.items()
        if any(kw in text for kw in keywords)
    ]


def infer_age_range(word_count: int) -> dict:
    """Coarse word-count → age_range estimate (requires human review)."""
    for threshold, age in AGE_RULES:
        if word_count <= threshold:
            return age
    return {"min": 6, "max": 12}


def process_file(src: Path) -> None:
    LABELED_DIR.mkdir(parents=True, exist_ok=True)
    dst = LABELED_DIR / src.name
    dst_tmp = dst.with_suffix(".tmp")
    now = datetime.now(timezone.utc).isoformat()
    with src.open(encoding="utf-8") as fin, dst_tmp.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            entry = json.loads(line)
            if not entry.get("age_range"):
                entry["age_range"] = infer_age_range(entry.get("word_count", 0))
            age_range = entry["age_range"]
            body = entry.get("body", "")
            title = entry.get("title", "")
            content_type = entry.get("content_type", "")
            entry["developmental_milestone"] = infer_developmental_milestones(age_range)
            entry["action_cues"] = detect_action_cues(body, content_type)
            entry["phonics"] = analyze_phonics(body, content_type)
            if not entry.get("themes"):
                entry["themes"] = detect_themes(body, title)
            entry["labeled_at"] = now
            fout.write(json.dumps(entry, ensure_ascii=False) + "\n")
    dst_tmp.rename(dst)
    print(f"labeled: {src.name} -> {dst}")


if __name__ == "__main__":
    for f in CLEANED_DIR.glob("*.jsonl"):
        process_file(f)
