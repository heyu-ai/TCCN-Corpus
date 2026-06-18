from scripts.clean import clean_body, normalize_fullwidth


def test_normalize_fullwidth_ascii():
    assert normalize_fullwidth("Ａ！") == "A!"


def test_normalize_fullwidth_tilde():
    assert normalize_fullwidth("～") == "~"


def test_normalize_fullwidth_ideographic_space():
    assert normalize_fullwidth("　") == " "


def test_normalize_fullwidth_leaves_cjk_untouched():
    assert normalize_fullwidth("你好") == "你好"


def test_clean_body_removes_control_chars():
    assert "\x01" not in clean_body("a\x01b")
    assert "\x0b" not in clean_body("a\x0bb")


def test_clean_body_collapses_excess_whitespace():
    assert clean_body("a\n\n\n\nb") == "a\n\nb"


def test_clean_body_decodes_html_entity_amp():
    assert clean_body("a &amp; b") == "a & b"


def test_clean_body_decodes_html_entity_lt_gt():
    assert clean_body("&lt;div&gt;") == "<div>"


def test_clean_body_strips_leading_trailing():
    assert clean_body("  hello  ") == "hello"


def test_clean_body_normalizes_fullwidth_inside():
    assert clean_body("Ａ") == "A"


def test_clean_body_empty_string():
    assert clean_body("") == ""
