"""Tests for lib/design_md_parser.py."""

import os
import pytest

from lib.design_md_parser import parse, DesignMd


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "design_md")


def test_parses_well_formed_design_md():
    result = parse(os.path.join(FIXTURES, "well_formed.md"))
    assert isinstance(result, DesignMd)
    assert result.tokens["name"] == "example"
    assert result.tokens["palette"]["background"] == "#0A1628"
    assert result.tokens["palette"]["primary_accent"] == "#E63946"
    assert result.tokens["typography"]["heading_family"] == "Inter"
    assert result.tokens["typography"]["heading_size_pt"] == 80
    assert "# Style: Example" in result.body
    assert "Lead with a stat" in result.body


def test_no_front_matter_returns_empty_tokens_full_body():
    result = parse(os.path.join(FIXTURES, "no_front_matter.md"))
    assert result.tokens == {}
    assert "# Just markdown" in result.body
    assert "No YAML at the top." in result.body


def test_only_front_matter_returns_empty_body():
    result = parse(os.path.join(FIXTURES, "empty_body.md"))
    assert result.tokens["name"] == "tokens_only"
    assert result.tokens["palette"]["background"] == "#FFFFFF"
    assert result.body.strip() == ""


def test_malformed_yaml_raises_with_path_in_message():
    with pytest.raises(ValueError) as exc_info:
        parse(os.path.join(FIXTURES, "malformed_yaml.md"))
    assert "malformed_yaml.md" in str(exc_info.value)


def test_missing_file_raises_filenotfounderror():
    with pytest.raises(FileNotFoundError):
        parse(os.path.join(FIXTURES, "nonexistent.md"))


def test_yaml_close_marker_must_be_on_own_line():
    """YAML front matter ends at a line that is exactly '---'."""
    import tempfile

    content = '---\nname: tricky\ndescription: "has --- inside"\n---\nbody here\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        result = parse(path)
        assert result.tokens["name"] == "tricky"
        assert result.tokens["description"] == "has --- inside"
        assert result.body.strip() == "body here"
    finally:
        os.unlink(path)


def test_returns_namedtuple_with_tokens_and_body_attrs():
    result = parse(os.path.join(FIXTURES, "well_formed.md"))
    assert hasattr(result, "tokens")
    assert hasattr(result, "body")
    tokens, body = result
    assert isinstance(tokens, dict)
    assert isinstance(body, str)


def test_yaml_with_unicode_arrows_preserved():
    import tempfile

    content = '---\nname: arrows\nemphasis: "term → definition"\n---\n\nBody with → too.\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        result = parse(path)
        assert "→" in result.tokens["emphasis"]
        assert "→" in result.body
    finally:
        os.unlink(path)


def test_empty_file_returns_empty_tokens_empty_body():
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("")
        path = f.name
    try:
        result = parse(path)
        assert result.tokens == {}
        assert result.body == ""
    finally:
        os.unlink(path)


def test_yaml_with_nested_dicts_round_trips():
    """Nested dicts (palette, typography, layout) survive parsing."""
    import tempfile

    content = '---\npalette:\n  background: "#000"\n  accent: "#FFF"\nlayout:\n  grid_cols: 12\n  density: "low"\n---\n\nBody.\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        result = parse(path)
        assert result.tokens["palette"]["background"] == "#000"
        assert result.tokens["palette"]["accent"] == "#FFF"
        assert result.tokens["layout"]["grid_cols"] == 12
        assert result.tokens["layout"]["density"] == "low"
    finally:
        os.unlink(path)
