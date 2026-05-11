"""Snapshot-style tests for prompt composition in styled-carousel."""

import os
import sys

KIT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, KIT_DIR)
sys.path.insert(0, os.path.join(KIT_DIR, "skills", "styled-carousel", "scripts"))

# Import the generator's helpers directly. The module name uses underscores
# because Python's import system converts hyphens.
import importlib.util
SCRIPT_PATH = os.path.join(
    KIT_DIR, "skills", "styled-carousel", "scripts", "generate_styled_carousel.py")
spec = importlib.util.spec_from_file_location("generate_styled_carousel", SCRIPT_PATH)
assert spec is not None
assert spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

compose_prompt = mod.compose_prompt
serialize_tokens = mod.serialize_tokens

# v0.7.0: parse_script lives in script_parser and returns ParsedScript.
# Wrap it in a tuple-returning shim so legacy tests asserting (role, body) tuples
# keep their semantics.
import script_parser as _script_parser_mod  # noqa: E402


def parse_script(path):
    parsed = _script_parser_mod.parse_script(path)
    return [(s.slot_role, s.body) for s in parsed.slides]


def test_serialize_tokens_flat_dict():
    tokens = {"image_treatment": "minimal_flat_icons"}
    out = serialize_tokens(tokens)
    assert "image_treatment: minimal_flat_icons" in out


def test_serialize_tokens_nested_palette():
    tokens = {"palette": {"background": "#000", "text": "#FFF"}}
    out = serialize_tokens(tokens)
    assert "palette.background: #000" in out
    assert "palette.text: #FFF" in out


def test_serialize_tokens_deeply_nested():
    tokens = {"a": {"b": {"c": "deep"}}}
    out = serialize_tokens(tokens)
    assert "a.b.c: deep" in out


def test_compose_prompt_includes_all_three_sections():
    tokens = {"palette": {"background": "#000"}}
    style_body = "**For:** test."
    prompt = compose_prompt(tokens, style_body, role="HOOK", body="hook text",
                            slide_idx=0, total_slides=6)
    assert "# Tokens" in prompt
    assert "palette.background: #000" in prompt
    assert "# Style intent" in prompt
    assert "**For:** test." in prompt
    assert "# Slide intent" in prompt
    assert "slide 1 of 6, role: HOOK" in prompt
    # v0.7.1: body is wrapped in quotes under a "slide text:" label.
    assert 'slide text:\n"hook text"' in prompt


def test_compose_prompt_zero_indexes_correctly():
    """slide_idx is 0-based but the prompt shows 1-based slide numbers."""
    tokens = {}
    prompt = compose_prompt(tokens, "", role="X", body="t", slide_idx=4, total_slides=6)
    assert "slide 5 of 6" in prompt


def test_parse_script_six_section_carousel():
    import tempfile

    script = """# HOOK
hook line

# REVEAL
reveal line

# SETUP
setup line

# EXAMPLES
1. one
2. two

# OUTCOME
outcome line

# CTA
cta line
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        sections = parse_script(path)
        assert len(sections) == 6
        assert sections[0] == ("HOOK", "hook line")
        assert sections[3][0] == "EXAMPLES"
        assert "1. one" in sections[3][1]
    finally:
        os.unlink(path)


def test_parse_script_handles_empty_section():
    """v0.7.0: an empty body in a slot is preserved as empty string."""
    import tempfile

    # Provide a full narrative carousel with one empty slot body.
    script = (
        "# HOOK\n"
        "\n"
        "# REVEAL\nreveal line\n\n"
        "# SETUP\nsetup line\n\n"
        "# EXAMPLES\nexamples line\n\n"
        "# OUTCOME\noutcome line\n\n"
        "# CTA\ncta line\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(script)
        path = f.name
    try:
        sections = parse_script(path)
        assert len(sections) == 6
        assert sections[0] == ("HOOK", "")
        assert sections[1] == ("REVEAL", "reveal line")
    finally:
        os.unlink(path)


def test_parse_script_no_sections_raises():
    """v0.7.0: a body with no headings raises (narrative requires HOOK)."""
    import tempfile
    import pytest

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("just prose, no headings")
        path = f.name
    try:
        with pytest.raises(ValueError):
            parse_script(path)
    finally:
        os.unlink(path)


def test_strip_meta_sections_removes_when_to_swap():
    strip_meta_sections = mod.strip_meta_sections

    body = (
        "# Style: Test\n\n"
        "Mood: bold.\n\n"
        "## Do\n- lead with stat\n\n"
        "## When to swap\n- use a different style for X\n\n"
        "## Don't\n- texture\n"
    )
    result = strip_meta_sections(body)
    assert "When to swap" not in result
    assert "## Do" in result
    assert "## Don't" in result
    assert "Mood: bold." in result


def test_strip_meta_sections_handles_alt_titles():
    strip_meta_sections = mod.strip_meta_sections

    for heading in [
        "## When to swap to a different style",
        "## Style swap guidance",
    ]:
        body = f"intro line.\n\n{heading}\nstuff.\n\n## Do\n- foo\n"
        result = strip_meta_sections(body)
        assert heading not in result
        assert "## Do" in result


def test_strip_meta_sections_no_op_when_absent():
    strip_meta_sections = mod.strip_meta_sections

    body = "# title\n\n## Do\n- foo\n\n## Don't\n- bar\n"
    assert strip_meta_sections(body) == body


def test_compose_prompt_leads_with_slide_intent():
    tokens = {"palette": {"background": "#FFFFFF"}}
    style_body = (
        "# Style: Test\n\n"
        "Mood: bold.\n\n"
        "## When to swap\n- use other for X\n\n"
        "## Do\n- lead with stat\n"
    )
    out = compose_prompt(
        tokens, style_body,
        role="HOOK", body="hook text", slide_idx=1, total_slides=6,
    )

    intent_pos = out.find("hook text")
    tokens_pos = out.find("background")
    style_pos = out.find("Mood: bold.")
    assert intent_pos != -1 and tokens_pos != -1 and style_pos != -1
    assert intent_pos < tokens_pos < style_pos

    # Meta sections should be stripped.
    assert "When to swap" not in out


def test_compose_prompt_includes_slide_n_of_m_for_variable_count():
    tokens = {"palette": {"background": "#FFFFFF"}}
    style_body = "# Style\n\n## Do\n- foo\n"
    out = compose_prompt(
        tokens, style_body,
        role="ITEM", body="item body", slide_idx=3, total_slides=9,
    )
    assert "slide 4 of 9" in out
    assert "ITEM" in out


def test_compose_prompt_includes_literal_text_framing():
    """v0.7.1: slide body must be framed as typography, not as illustration.

    Slides like '3 columns of feature icons' previously rendered as actual
    icon grids. The framing directive prevents the model from treating the
    body text as visual instructions.
    """
    out = compose_prompt(
        tokens={"palette": {"background": "#FFFFFF"}},
        style_body="# Style\n\n## Do\n- foo\n",
        role="ITEM",
        body="3 columns of feature icons",
        slide_idx=0,
        total_slides=3,
    )
    assert "render the slide text below verbatim as the foreground typography" in out.lower()
    assert "do not illustrate" in out.lower() or "do NOT illustrate" in out
    assert '"3 columns of feature icons"' in out


def test_compose_prompt_uses_screenshot_native_framing_by_default():
    out = compose_prompt(
        tokens={"palette": {"background": "#FFFFFF"}},  # no image_treatment
        style_body="# Style\n",
        role="HOOK",
        body="hook line",
        slide_idx=0,
        total_slides=3,
    )
    assert "typography-driven social carousel slide" in out.lower()
    assert "the text is the design" in out.lower()


def test_compose_prompt_uses_screenshot_native_framing_when_explicit():
    out = compose_prompt(
        tokens={"image_treatment": "screenshot_native"},
        style_body="# Style\n",
        role="HOOK",
        body="hook line",
        slide_idx=0,
        total_slides=3,
    )
    assert "typography-driven" in out.lower()


def test_compose_prompt_uses_iphone_candid_framing_for_character_styles():
    out = compose_prompt(
        tokens={"image_treatment": "iphone_candid"},
        style_body="# Style\n",
        role="HOOK",
        body="hook line",
        slide_idx=0,
        total_slides=3,
    )
    assert "candid iphone-style photograph" in out.lower()
    # Does NOT use the typography framing.
    assert "typography-driven" not in out.lower()
    assert "the text is the design" not in out.lower()


def test_compose_prompt_unknown_image_treatment_falls_back_to_default():
    out = compose_prompt(
        tokens={"image_treatment": "this_does_not_exist"},
        style_body="# Style\n",
        role="HOOK",
        body="hook line",
        slide_idx=0,
        total_slides=3,
    )
    # Falls back to screenshot_native default.
    assert "typography-driven" in out.lower()


def test_compose_prompt_iphone_candid_uses_exact_text_directive():
    out = compose_prompt(
        tokens={"image_treatment": "iphone_candid"},
        style_body="# Style\n",
        role="HOOK",
        body="this is the caption text",
        slide_idx=0,
        total_slides=3,
    )
    # v0.7.5 load-bearing phrases: render-this-exact-text + verbatim caption
    # + strengthened no-paraphrase clause.
    assert "Render this exact text" in out
    assert '"this is the caption text"' in out
    assert "Do not paraphrase, abbreviate, or summarize" in out
    # Should NOT include a separate "slide text:" block (template handles it)
    assert "slide text:" not in out


def test_compose_prompt_screenshot_native_keeps_v071_shape():
    out = compose_prompt(
        tokens={"image_treatment": "screenshot_native"},
        style_body="# Style\n",
        role="HOOK",
        body="hook body",
        slide_idx=0,
        total_slides=3,
    )
    # Existing v0.7.1 shape preserved
    assert "typography-driven" in out.lower()
    assert "slide text:" in out
    assert '"hook body"' in out


def test_compose_prompt_screenshot_native_preserves_long_body():
    """v0.7.4: truncation is gone; screenshot_native passes long bodies through verbatim."""
    long_body = "this body should appear verbatim under screenshot_native with no truncation applied at all"
    out = compose_prompt(
        tokens={"image_treatment": "screenshot_native"},
        style_body="",
        role="ITEM",
        body=long_body,
        slide_idx=0,
        total_slides=3,
    )
    assert long_body in out


def test_compose_prompt_iphone_candid_passes_full_caption_verbatim():
    """v0.7.4: auto-truncation removed. Long iphone_candid captions pass through."""
    long_body = "this caption text is intentionally written to be quite long and must pass through verbatim now that the v0.7.3 truncation has been removed"
    out = compose_prompt(
        tokens={"image_treatment": "iphone_candid"},
        style_body="",
        role="ITEM",
        body=long_body,
        slide_idx=0,
        total_slides=3,
    )
    # Full body appears verbatim, no ellipsis injected.
    assert long_body in out
    assert "..." not in out
    assert "Do not paraphrase, abbreviate, or summarize" in out


def test_compose_prompt_iphone_candid_substitutes_visual_directive():
    out = compose_prompt(
        tokens={"image_treatment": "iphone_candid"},
        style_body="",
        role="HOOK",
        body="caption text",
        slide_idx=0,
        total_slides=3,
        visual="matt at desk leaning back, hand on forehead, exasperated",
    )
    assert "matt at desk leaning back, hand on forehead, exasperated" in out
    assert "Render this exact text" in out
    assert '"caption text"' in out


def test_compose_prompt_iphone_candid_falls_back_when_no_visual():
    out = compose_prompt(
        tokens={"image_treatment": "iphone_candid"},
        style_body="",
        role="HOOK",
        body="caption",
        slide_idx=0,
        total_slides=3,
        # no visual passed
    )
    # Falls back to generic but still character-anchored
    assert "candid moment" in out.lower()
    assert "Render this exact text" in out


def test_compose_prompt_iphone_candid_is_slim():
    """v0.7.5: iphone_candid prompts must be lean -- no token dump, no DESIGN.md verbatim."""
    out = compose_prompt(
        tokens={
            "image_treatment": "iphone_candid",
            "palette": {"background": "#FFFFFF", "primary_accent": "#F43F5E"},
            "typography": {"heading_family": "Inter"},
            "layout": {"grid_cols": 12, "format": "iphone_portrait"},
        },
        style_body=(
            "# Style: Social Native\n\n"
            "**For:** UGC carousels.\n\n"
            "## Do\n- Anchor every slide\n\n"
            "## Don't\n- Type-forward slides\n"
        ),
        role="ITEM",
        body="tell #1: it has exactly 6 slides. not 5. not 7.",
        slide_idx=1,
        total_slides=7,
        visual="Matt at his desk leaning back, hand on chin",
    )
    # The prompt must NOT contain serialized token noise.
    assert "palette.background" not in out
    assert "layout.grid_cols" not in out
    assert "image_treatment: iphone_candid" not in out
    # The prompt must NOT contain DESIGN.md verbatim.
    assert "**For:** UGC carousels." not in out
    assert "## Do" not in out
    assert "## Don't" not in out
    # The prompt MUST contain the visual + caption.
    assert "Matt at his desk leaning back, hand on chin" in out
    assert '"tell #1: it has exactly 6 slides. not 5. not 7."' in out
    # The prompt should be slim.
    assert len(out) < 1200, f"iphone_candid prompt is too long: {len(out)} chars"
