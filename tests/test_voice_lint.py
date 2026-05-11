"""Tests for lib/voice_lint.py."""

import os

from lib.voice_lint import lint_text, Violation


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "voice_lint")


def _read(name: str) -> str:
    with open(os.path.join(FIXTURES, name)) as f:
        return f.read()


def test_clean_text_returns_empty():
    assert lint_text(_read("clean.md")) == []


def test_em_dash_detected():
    violations = lint_text(_read("em_dash.md"))
    assert len(violations) == 1
    v = violations[0]
    assert isinstance(v, Violation)
    assert v.severity == "error"
    assert v.rule_id == "em_dash"
    assert v.line == 4  # line 4 in the fixture
    assert "—" in v.snippet


def test_multiple_em_dashes_one_per_occurrence():
    text = "a — b — c\n"
    violations = lint_text(text)
    assert len(violations) == 2
    assert all(v.rule_id == "em_dash" for v in violations)
    assert violations[0].column < violations[1].column


def test_pattern_not_x_its_y():
    violations = lint_text(_read("patterns.md"))
    rule_ids = [v.rule_id for v in violations]
    assert "pattern_not_x_its_y" in rule_ids


def test_pattern_dont_just():
    violations = lint_text(_read("patterns.md"))
    rule_ids = [v.rule_id for v in violations]
    assert "pattern_dont_just" in rule_ids


def test_pattern_not_just():
    violations = lint_text(_read("patterns.md"))
    rule_ids = [v.rule_id for v in violations]
    assert "pattern_not_just" in rule_ids


def test_pattern_truth_is():
    violations = lint_text(_read("patterns.md"))
    rule_ids = [v.rule_id for v in violations]
    assert "pattern_truth_is" in rule_ids


def test_pattern_negative_no_false_positives():
    text = "this is not bad. it's a sunny day. don't worry.\n"
    violations = lint_text(text)
    pattern_violations = [v for v in violations if v.rule_id.startswith("pattern_")]
    assert pattern_violations == []


def test_banned_words_detected():
    violations = lint_text(_read("banned_words.md"))
    eng = [v for v in violations if v.rule_id == "banned_word_eng_jargon"]
    assert len(eng) == 4
    snippets = [v.snippet for v in eng]
    assert any("deprecated" in s for s in snippets)
    assert any("leverage" in s for s in snippets)
    assert any("optimize" in s for s in snippets)
    assert any("docstring" in s for s in snippets)


def test_banned_words_word_boundary():
    violations = lint_text("a deprecation event happened.\n")
    eng = [v for v in violations if v.rule_id == "banned_word_eng_jargon"]
    assert eng == []


def test_brand_avoid_literal_phrase_detected():
    text = "let's circle back next week.\n"
    violations = lint_text(
        text,
        brand_voice_path=os.path.join(FIXTURES, "brand_voice_with_avoid.md"),
    )
    rule_ids = [v.rule_id for v in violations]
    assert any(r.startswith("brand_avoid_") for r in rule_ids)
    brand = [v for v in violations if v.rule_id.startswith("brand_avoid_")]
    assert any("circle back" in v.snippet for v in brand)


def test_brand_avoid_regex_form_detected():
    text = "watch the blast radius on this change.\n"
    violations = lint_text(
        text,
        brand_voice_path=os.path.join(FIXTURES, "brand_voice_with_avoid.md"),
    )
    brand = [v for v in violations if v.rule_id.startswith("brand_avoid_")]
    assert any("blast radius" in v.snippet for v in brand)


def test_brand_avoid_missing_file_silently_ignored():
    text = "this is fine.\n"
    violations = lint_text(text, brand_voice_path="/nonexistent/path.md")
    assert violations == []


def test_brand_avoid_missing_section_silently_ignored():
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("# brand voice\n\nNo Avoid section here.\n")
        path = f.name
    violations = lint_text("a clean line.\n", brand_voice_path=path)
    assert violations == []


def test_kit_and_brand_rules_both_apply():
    text = "it's not the model, it's the prompt.\n"
    violations = lint_text(
        text,
        brand_voice_path=os.path.join(FIXTURES, "brand_voice_with_avoid.md"),
    )
    rule_ids = [v.rule_id for v in violations]
    assert "pattern_not_x_its_y" in rule_ids
