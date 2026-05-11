"""Tests for lib/hook_patterns.py."""

import pytest

from lib.hook_patterns import HOOK_PATTERNS, get_pattern, list_patterns


EXPECTED_PATTERNS = {
    "single_claim",
    "question",
    "scene",
    "dialogue",
    "contrast",
    "observation",
}


def test_six_patterns_enumerated():
    assert set(HOOK_PATTERNS.keys()) == EXPECTED_PATTERNS


def test_each_pattern_has_required_fields():
    for name, entry in HOOK_PATTERNS.items():
        assert "description" in entry, name
        assert "exemplars" in entry, name
        assert "when_to_use" in entry, name
        assert isinstance(entry["exemplars"], list)
        assert len(entry["exemplars"]) >= 1


def test_pattern_names_lowercase_underscore():
    for name in HOOK_PATTERNS:
        assert name == name.lower()
        assert " " not in name


def test_exemplars_are_lowercase_voice():
    for name, entry in HOOK_PATTERNS.items():
        for exemplar in entry["exemplars"]:
            assert exemplar[0] == exemplar[0].lower(), f"{name}: {exemplar}"


def test_get_pattern_returns_entry():
    p = get_pattern("single_claim")
    assert "description" in p


def test_get_pattern_unknown_raises():
    with pytest.raises(KeyError):
        get_pattern("not_a_pattern")


def test_list_patterns_sorted():
    out = list_patterns()
    assert out == sorted(EXPECTED_PATTERNS)


def test_no_em_dash_in_exemplars():
    for name, entry in HOOK_PATTERNS.items():
        for exemplar in entry["exemplars"]:
            assert "—" not in exemplar, f"{name}: em-dash in '{exemplar}'"


def test_references_doc_lists_all_patterns():
    """references/hook-patterns.md must mention every pattern in HOOK_PATTERNS."""
    import os
    here = os.path.dirname(__file__)
    doc_path = os.path.abspath(os.path.join(here, "..", "references", "hook-patterns.md"))
    with open(doc_path) as f:
        doc = f.read()
    for name in HOOK_PATTERNS:
        assert f"## {name}" in doc, f"hook-patterns.md missing section for {name}"
