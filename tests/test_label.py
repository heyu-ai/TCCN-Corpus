from scripts.label import (
    analyze_phonics,
    detect_action_cues,
    detect_themes,
    infer_age_range,
    infer_developmental_milestones,
)


# --- infer_developmental_milestones ---

def test_milestones_full_0_to_6():
    result = infer_developmental_milestones({"min": 0, "max": 6})
    assert result == [
        "language_0_1", "language_1_2", "language_2_3",
        "language_3_4", "language_4_5", "language_5_6",
    ]


def test_milestones_partial_overlap():
    result = infer_developmental_milestones({"min": 2, "max": 4})
    assert "language_2_3" in result
    assert "language_3_4" in result
    assert "language_0_1" not in result
    assert "language_4_5" not in result


def test_milestones_single_band():
    assert infer_developmental_milestones({"min": 0, "max": 1}) == ["language_0_1"]


def test_milestones_beyond_6_returns_empty():
    assert infer_developmental_milestones({"min": 7, "max": 10}) == []


def test_milestones_age_range_max_at_boundary():
    # max=2 overlaps language_0_1 and language_1_2 only
    result = infer_developmental_milestones({"min": 0, "max": 2})
    assert "language_0_1" in result
    assert "language_1_2" in result
    assert "language_2_3" not in result


# --- detect_action_cues ---

def test_action_cues_clap_and_stomp():
    cues = detect_action_cues("小朋友一起拍手，踏步前進！", "nursery_rhyme")
    assert "拍手" in cues
    assert "踏步" in cues


def test_action_cues_spin():
    cues = detect_action_cues("轉圈轉圈不停歇", "nursery_rhyme")
    assert "轉圈" in cues


def test_action_cues_not_for_picture_book():
    cues = detect_action_cues("拍手跺腳轉圈揮手", "picture_book")
    assert cues == []


def test_action_cues_empty_body():
    assert detect_action_cues("", "nursery_rhyme") == []


def test_action_cues_no_match():
    assert detect_action_cues("小熊在睡覺", "nursery_rhyme") == []


def test_action_cues_no_duplicates():
    cues = detect_action_cues("拍手拍手再拍手", "nursery_rhyme")
    assert cues.count("拍手") == 1


# --- analyze_phonics ---

def test_phonics_repetition_ratio_two_thirds():
    body = "小星星\n小星星\n閃閃亮"
    result = analyze_phonics(body, "nursery_rhyme")
    assert "repetition_ratio" in result
    assert result["repetition_ratio"] == round(2 / 3, 2)


def test_phonics_no_repetition():
    body = "第一行\n第二行\n第三行"
    result = analyze_phonics(body, "nursery_rhyme")
    assert result["repetition_ratio"] == 0.0


def test_phonics_all_same_lines():
    body = "一閃一閃\n一閃一閃\n一閃一閃"
    result = analyze_phonics(body, "nursery_rhyme")
    assert result["repetition_ratio"] == 1.0


def test_phonics_empty_body():
    assert analyze_phonics("", "nursery_rhyme") == {}


def test_phonics_single_line():
    assert analyze_phonics("只有一行", "nursery_rhyme") == {}


def test_phonics_not_for_picture_book():
    assert analyze_phonics("一行\n兩行\n一行", "picture_book") == {}


# --- detect_themes ---

def test_themes_animal_from_body():
    themes = detect_themes("小狗在跑步", "")
    assert "動物" in themes


def test_themes_nature_from_title():
    themes = detect_themes("", "天空和太陽")
    assert "自然" in themes


def test_themes_multiple_themes():
    themes = detect_themes("媽媽帶著小狗散步", "")
    assert "動物" in themes
    assert "家庭" in themes


def test_themes_emotion():
    themes = detect_themes("我好開心", "")
    assert "情緒" in themes


def test_themes_empty_text():
    assert detect_themes("", "") == []


def test_themes_body_sensory():
    themes = detect_themes("眼睛和耳朵都要用", "")
    assert "身體認知" in themes


# --- infer_age_range ---

def test_infer_age_range_very_short():
    assert infer_age_range(50) == {"min": 0, "max": 3}


def test_infer_age_range_at_threshold():
    assert infer_age_range(150) == {"min": 0, "max": 3}


def test_infer_age_range_medium():
    assert infer_age_range(300) == {"min": 2, "max": 4}


def test_infer_age_range_older():
    assert infer_age_range(900) == {"min": 5, "max": 8}


def test_infer_age_range_very_long():
    assert infer_age_range(2000) == {"min": 6, "max": 12}
