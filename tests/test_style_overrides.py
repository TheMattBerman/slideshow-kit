import os
import pytest


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "styles")


def test_load_style_overrides_returns_map_for_present_yaml():
    from lib.style_overrides import load_style_overrides
    result = load_style_overrides(os.path.join(FIXTURES, "word_cap_override"))
    assert result == {
        "HOOK": (3, 8),
        "ITEM": (6, 12),
        "CTA": (3, 6),
    }


def test_load_style_overrides_returns_empty_when_file_absent():
    from lib.style_overrides import load_style_overrides
    result = load_style_overrides(os.path.join(FIXTURES, "no_override"))
    assert result == {}


def test_load_style_overrides_returns_empty_when_dir_missing():
    from lib.style_overrides import load_style_overrides
    result = load_style_overrides("/nonexistent/path/asdfasdf")
    assert result == {}


def test_load_style_overrides_rejects_non_list_value(tmp_path):
    from lib.style_overrides import load_style_overrides
    bad = tmp_path / "style.yaml"
    bad.write_text("word_count_override:\n  HOOK: 5\n")
    with pytest.raises(ValueError, match="HOOK"):
        load_style_overrides(str(tmp_path))


def test_load_style_overrides_rejects_min_greater_than_max(tmp_path):
    from lib.style_overrides import load_style_overrides
    bad = tmp_path / "style.yaml"
    bad.write_text("word_count_override:\n  HOOK: [10, 5]\n")
    with pytest.raises(ValueError, match="min.*max"):
        load_style_overrides(str(tmp_path))


def test_load_style_overrides_rejects_negative(tmp_path):
    from lib.style_overrides import load_style_overrides
    bad = tmp_path / "style.yaml"
    bad.write_text("word_count_override:\n  HOOK: [-1, 5]\n")
    with pytest.raises(ValueError, match="non-negative"):
        load_style_overrides(str(tmp_path))


def test_merge_word_count_override_replaces_format_range():
    from lib.style_overrides import merge_word_count_override
    format_range = (15, 50)
    style_override = (6, 12)
    assert merge_word_count_override(format_range, style_override) == (6, 12)


def test_merge_word_count_override_returns_format_range_when_override_none():
    from lib.style_overrides import merge_word_count_override
    format_range = (15, 50)
    assert merge_word_count_override(format_range, None) == (15, 50)
