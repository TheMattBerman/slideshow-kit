"""Tests for format-aware script parser."""

import importlib.util
import os
import sys

import pytest


SCRIPT_PARSER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "skills", "styled-carousel", "scripts", "script_parser.py",
)
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "formats")


def _load_parser():
    spec = importlib.util.spec_from_file_location("script_parser", SCRIPT_PARSER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["script_parser"] = module
    spec.loader.exec_module(module)
    return module


def test_parses_narrative_with_frontmatter():
    parser = _load_parser()
    parsed = parser.parse_script(os.path.join(FIXTURES, "narrative_ok.md"))
    assert parsed.format_name == "narrative"
    assert parsed.close_action == "save"
    assert len(parsed.slides) == 6
    assert [s.slot_role for s in parsed.slides] == \
        ["HOOK", "REVEAL", "SETUP", "EXAMPLES", "OUTCOME", "CTA"]


def test_parses_numbered_diagnostic_with_4_items():
    parser = _load_parser()
    parsed = parser.parse_script(os.path.join(FIXTURES, "numbered_diagnostic_ok.md"))
    assert parsed.format_name == "numbered_diagnostic"
    assert parsed.close_action == "save"
    # HOOK + 4 ITEM + FIX + CTA = 7
    assert len(parsed.slides) == 7
    assert [s.slot_role for s in parsed.slides] == \
        ["HOOK", "ITEM", "ITEM", "ITEM", "ITEM", "FIX", "CTA"]


def test_parses_no_frontmatter_defaults_to_narrative():
    parser = _load_parser()
    parsed = parser.parse_script(os.path.join(FIXTURES, "no_frontmatter.md"))
    assert parsed.format_name == "narrative"
    assert parsed.close_action == "save"
    assert len(parsed.slides) == 6


def test_unknown_format_raises():
    parser = _load_parser()
    with pytest.raises(ValueError, match="unknown format"):
        parser.parse_script(os.path.join(FIXTURES, "unknown_format.md"))


def test_bad_count_raises_at_validation():
    parser = _load_parser()
    with pytest.raises(ValueError, match="ITEM"):
        parser.parse_script(os.path.join(FIXTURES, "bad_count.md"))


def test_alias_match_case_insensitive():
    parser = _load_parser()
    parsed = parser.parse_script(os.path.join(FIXTURES, "receipt_context_ok.md"))
    assert parsed.format_name == "receipt_context"
    assert parsed.close_action == "comment"
    assert len(parsed.slides) == 5


def test_heading_with_trailing_text():
    """`# TELL #1: it has 6 slides` should match TELL alias and ignore the title."""
    parser = _load_parser()
    parsed = parser.parse_script(os.path.join(FIXTURES, "numbered_diagnostic_ok.md"))
    item_slides = [s for s in parsed.slides if s.slot_role == "ITEM"]
    assert len(item_slides) == 4
    # Body should preserve full content including the trailing title.
    assert any("tell #1" in s.body.lower() for s in item_slides)


@pytest.mark.parametrize("fixture,expected_count", [
    ("narrative_ok.md", 6),
    ("numbered_diagnostic_ok.md", 7),
    ("receipt_context_ok.md", 5),
    ("process_reveal_ok.md", 7),
    ("anatomy_breakdown_ok.md", 7),
    ("before_after_ok.md", 5),
    ("counter_narrative_ok.md", 5),
])
def test_all_formats_round_trip(fixture, expected_count):
    parser = _load_parser()
    parsed = parser.parse_script(os.path.join(FIXTURES, fixture))
    assert len(parsed.slides) == expected_count


def test_close_action_falls_back_to_format_default():
    """When frontmatter omits close_action, use format's default_close_action."""
    parser = _load_parser()
    # Write an inline fixture without close_action
    import tempfile
    content = (
        "---\n"
        "format: counter_narrative\n"
        "---\n\n"
        "# HOOK\nshort hook line.\n\n"
        "# THE_QUOTE\nthe dominant view stated in fifteen or twenty words exactly.\n\n"
        "# THE_QUESTION\nbut why does this hold across all cases that we have seen?\n\n"
        "# THE_REAL_ANSWER\nthe real answer is a specific named framework that the kit can identify in twenty plus words.\n\n"
        "# CTA\ncomment if you want the framework write-up sent to your DMs today.\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(content)
        path = f.name
    parsed = parser.parse_script(path)
    # counter_narrative defaults to comment
    assert parsed.close_action == "comment"


def test_unclosed_frontmatter_raises():
    parser = _load_parser()
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("---\nformat: narrative\n# never closes\n# HOOK\nfoo\n")
        path = f.name
    with pytest.raises(ValueError, match="frontmatter"):
        parser.parse_script(path)


def test_malformed_yaml_in_frontmatter_raises():
    parser = _load_parser()
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("---\nformat: : :\n---\n\n# HOOK\nfoo\n")
        path = f.name
    with pytest.raises(ValueError, match="frontmatter"):
        parser.parse_script(path)


def test_invalid_close_action_raises():
    parser = _load_parser()
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(
            "---\nformat: narrative\nclose_action: bogus\n---\n\n"
            "# HOOK\nfoo\n# REVEAL\nbar\n# SETUP\nbaz\n"
            "# EXAMPLES\nqux\n# OUTCOME\nquux\n# CTA\ncomment.\n"
        )
        path = f.name
    with pytest.raises(ValueError, match="close_action"):
        parser.parse_script(path)


def test_heading_role_token_handles_underscore_digit():
    """`# STEP_1` should match the STEP alias (trailing underscore stripped)."""
    parser = _load_parser()
    import tempfile
    content = (
        "---\n"
        "format: process_reveal\n"
        "close_action: save\n"
        "---\n\n"
        "# HOOK\nhook line that is not too short to fail word count maybe.\n\n"
        "# STEP_1\nfirst step body line that is long enough to pass word counts.\n\n"
        "# STEP_2\nsecond step body line that is long enough to pass word counts.\n\n"
        "# STEP_3\nthird step body line that is long enough to pass word counts.\n\n"
        "# OUTCOME\nthe outcome body line that is long enough to pass word counts.\n\n"
        "# CTA\nsave this if you read it through to the end of the post.\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(content)
        path = f.name
    parsed = parser.parse_script(path)
    assert parsed.format_name == "process_reveal"
    step_slides = [s for s in parsed.slides if s.slot_role == "STEP"]
    assert len(step_slides) == 3
