"""Tests for lib/format_registry.py."""

import pytest

from lib.format_registry import (
    FormatDef,
    Slot,
    VALID_CLOSE_ACTIONS,
    get_format,
    list_formats,
)


def test_get_format_returns_format_def():
    fmt = get_format("narrative")
    assert isinstance(fmt, FormatDef)
    assert fmt.name == "narrative"
    assert fmt.default_close_action in VALID_CLOSE_ACTIONS
    assert len(fmt.slots) == 6


def test_narrative_slot_template():
    fmt = get_format("narrative")
    roles = [s.role for s in fmt.slots]
    assert roles == ["HOOK", "REVEAL", "SETUP", "EXAMPLES", "OUTCOME", "CTA"]


def test_slot_word_count_range():
    fmt = get_format("narrative")
    hook = fmt.slots[0]
    assert hook.word_count_min == 6
    assert hook.word_count_max == 15


def test_slot_aliases_uppercased():
    fmt = get_format("narrative")
    examples = fmt.slots[3]  # EXAMPLES slot
    for alias in examples.aliases:
        assert alias == alias.upper()


def test_get_format_unknown_name_raises():
    with pytest.raises(ValueError, match="unknown format"):
        get_format("nonexistent_format")


def test_list_formats_returns_sorted_list():
    formats = list_formats()
    assert "narrative" in formats
    assert formats == sorted(formats)


def test_get_format_invalid_close_action_raises(tmp_path, monkeypatch):
    bad = tmp_path / "bad_action.yaml"
    bad.write_text(
        "name: bad_action\n"
        "default_close_action: bogus\n"
        "slots:\n"
        "  - role: HOOK\n"
        "    count: 1\n"
        "    word_count_range: [6, 15]\n"
        "    aliases: [HOOK]\n"
    )
    import lib.format_registry as fr
    monkeypatch.setattr(fr, "_formats_dir", lambda: str(tmp_path))
    with pytest.raises(ValueError, match="default_close_action"):
        get_format("bad_action")


def test_get_format_count_min_greater_than_max_raises(tmp_path, monkeypatch):
    bad = tmp_path / "bad_range.yaml"
    bad.write_text(
        "name: bad_range\n"
        "default_close_action: save\n"
        "slots:\n"
        "  - role: ITEM\n"
        "    count_range: [5, 2]\n"
        "    word_count_range: [10, 20]\n"
        "    aliases: [ITEM]\n"
    )
    import lib.format_registry as fr
    monkeypatch.setattr(fr, "_formats_dir", lambda: str(tmp_path))
    with pytest.raises(ValueError, match="count_min > count_max"):
        get_format("bad_range")


def test_get_format_non_dict_slot_raises(tmp_path, monkeypatch):
    bad = tmp_path / "bad_slot.yaml"
    bad.write_text(
        "name: bad_slot\n"
        "default_close_action: save\n"
        "slots:\n"
        "  - this is a bare string\n"
    )
    import lib.format_registry as fr
    monkeypatch.setattr(fr, "_formats_dir", lambda: str(tmp_path))
    with pytest.raises(ValueError, match="must be a mapping"):
        get_format("bad_slot")


def test_all_kit_formats_load():
    """Every YAML file in references/formats/ must parse without error."""
    for name in list_formats():
        fmt = get_format(name)
        assert fmt.name == name
        assert len(fmt.slots) >= 3  # at minimum HOOK + body + CTA
        assert fmt.slots[0].role == "HOOK"
        assert fmt.slots[-1].role == "CTA"


def test_kit_ships_seven_formats():
    expected = {
        "narrative",
        "numbered_diagnostic",
        "receipt_context",
        "process_reveal",
        "anatomy_breakdown",
        "before_after",
        "counter_narrative",
    }
    assert set(list_formats()) == expected
