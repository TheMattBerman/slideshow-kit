"""Tests for lib/visual_director.py.

These tests do NOT call the OpenAI API. They validate parsing, schema, and
direct_scenes behavior with a stubbed _call_openai.
"""

import os
import sys

KIT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if KIT_DIR not in sys.path:
    sys.path.insert(0, KIT_DIR)

from lib.visual_director import (  # noqa: E402
    CHARACTER_DRIVEN_TREATMENTS,
    DIRECT_SCENES_SYSTEM_PROMPT,
)


def test_character_driven_treatments_set_includes_iphone_candid():
    assert "iphone_candid" in CHARACTER_DRIVEN_TREATMENTS


def test_direct_scenes_system_prompt_guides_cta_visual_cues():
    prompt = DIRECT_SCENES_SYSTEM_PROMPT.lower()
    assert "cta slide" in prompt
    assert "save" in prompt
    assert "bookmark" in prompt
    assert "book" in prompt
    assert "share" in prompt
    assert "arrow" in prompt
    assert "send" in prompt
    assert "dm" in prompt
    assert "comment" in prompt
    assert "bubble" in prompt
    assert "typing" in prompt
    assert "soft" in prompt
    assert "no ui cue" in prompt
    assert "facial close" in prompt


def test_scene_brief_namedtuple_shape():
    from lib.visual_director import SceneBrief
    sb = SceneBrief(role="HOOK", scene_brief="matt at desk", tone="thoughtful")
    assert sb.role == "HOOK"
    assert sb.scene_brief == "matt at desk"
    assert sb.tone == "thoughtful"


def test_scene_direction_namedtuple_shape():
    from lib.visual_director import SceneBrief, SceneDirection
    sd = SceneDirection(
        slides=[SceneBrief(role="HOOK", scene_brief="x", tone="y")],
        source="stage_3",
    )
    assert len(sd.slides) == 1
    assert sd.source == "stage_3"


def test_scene_direction_to_markdown_roundtrip():
    from lib.visual_director import (
        SceneBrief, SceneDirection,
        scene_direction_to_markdown, scene_direction_from_markdown,
    )
    original = SceneDirection(
        slides=[
            SceneBrief(role="HOOK", scene_brief="matt at standing desk, late evening lamp warmth, mid-thought.", tone="observational"),
            SceneBrief(role="ITEM", scene_brief="closeup of laptop screen showing carousel feed.", tone="diagnostic"),
        ],
        source="stage_3",
    )
    md = scene_direction_to_markdown(original)
    assert "Scene direction" in md
    assert "stage_3" in md
    assert "## Slide 1 (HOOK)" in md
    assert "## Slide 2 (ITEM)" in md
    parsed = scene_direction_from_markdown(md)
    assert parsed == original


def test_scene_direction_from_markdown_tolerates_renderer_fallback_source():
    from lib.visual_director import scene_direction_from_markdown
    md = (
        "# Scene direction (source: renderer_fallback)\n\n"
        "## Slide 1 (HOOK)\n"
        "**Tone:** punchy\n"
        "**Scene:** desk shot\n"
    )
    sd = scene_direction_from_markdown(md)
    assert sd.source == "renderer_fallback"
    assert len(sd.slides) == 1
    assert sd.slides[0].role == "HOOK"
    assert sd.slides[0].tone == "punchy"


def test_scene_direction_from_markdown_rejects_unknown_source():
    from lib.visual_director import scene_direction_from_markdown
    md = "# Scene direction (source: bogus)\n\n## Slide 1 (HOOK)\n**Scene:** x\n"
    import pytest
    with pytest.raises(ValueError, match="source"):
        scene_direction_from_markdown(md)


def test_direct_scenes_eager_passes_visual_hook_and_arc(monkeypatch):
    """Eager call: visual_hook + concept_arc populated, source = stage_3."""
    from lib import visual_director as vd

    captured = {}

    def fake_call(system, user, api_key, model):
        captured["user"] = user
        captured["system"] = system
        return (
            '[{"slide_idx": 0, "visual": "matt at desk, italian street view through window, espresso steam.", "rationale": "matches the italy concept arc"}]'
        )

    monkeypatch.setattr(vd, "_call_openai", fake_call)

    parsed = [("HOOK", "tuesday morning. i was in italy.", "")]
    sd = vd.direct_scenes(
        parsed_slides=parsed,
        visual_hook="italian street, espresso, golden hour",
        concept_arc="how a 3-day trip became my best content week",
        brand_design="DESIGN body content",
        character_profile="matt is a 35-year-old founder",
        api_key="sk-test",
    )
    assert isinstance(sd, vd.SceneDirection)
    assert sd.source == "stage_3"
    assert len(sd.slides) == 1
    assert sd.slides[0].role == "HOOK"
    assert "italy" in captured["user"].lower() or "italian" in captured["user"].lower()
    assert "italian street" in captured["user"]
    assert "3-day trip" in captured["user"]


def test_direct_scenes_lazy_omits_optional_context(monkeypatch):
    """Lazy call: visual_hook + concept_arc absent, source = renderer_fallback."""
    from lib import visual_director as vd

    captured = {}

    def fake_call(system, user, api_key, model):
        captured["user"] = user
        return '[{"slide_idx": 0, "visual": "matt at standing desk, late evening lamp.", "rationale": ""}]'

    monkeypatch.setattr(vd, "_call_openai", fake_call)

    parsed = [("HOOK", "the four tells of every AI carousel.", "")]
    sd = vd.direct_scenes(
        parsed_slides=parsed,
        brand_design="DESIGN body",
        character_profile=None,
        api_key="sk-test",
    )
    assert sd.source == "renderer_fallback"
    assert "Visual hook" not in captured["user"]
    assert "Concept arc" not in captured["user"]


def test_direct_scenes_returns_one_scene_per_slide(monkeypatch):
    from lib import visual_director as vd

    monkeypatch.setattr(vd, "_call_openai", lambda *a, **k: (
        '[{"slide_idx": 0, "visual": "scene 0", "rationale": ""},'
        ' {"slide_idx": 1, "visual": "scene 1", "rationale": ""},'
        ' {"slide_idx": 2, "visual": "scene 2", "rationale": ""}]'
    ))

    parsed = [
        ("HOOK", "h", ""), ("ITEM", "i1", ""), ("CTA", "c", ""),
    ]
    sd = vd.direct_scenes(
        parsed_slides=parsed, brand_design="d", api_key="sk-test"
    )
    assert len(sd.slides) == 3
    assert [s.role for s in sd.slides] == ["HOOK", "ITEM", "CTA"]


def test_direct_scenes_user_message_size_under_2000_chars(monkeypatch):
    from lib import visual_director as vd

    captured = {}
    monkeypatch.setattr(vd, "_call_openai", lambda s, u, k, m: (
        captured.setdefault("user", u),
        '[{"slide_idx": 0, "visual": "x", "rationale": ""}]',
    )[1])

    parsed = [("HOOK", "h", "")]
    vd.direct_scenes(
        parsed_slides=parsed,
        visual_hook="italian street, espresso, golden hour",
        concept_arc="3-day trip became my best content week",
        brand_design="DESIGN body content " * 30,
        character_profile="matt is a founder " * 30,
        api_key="sk-test",
    )
    assert len(captured["user"]) <= 2000, (
        f"direct_scenes user message exceeds 2000 chars: "
        f"{len(captured['user'])}"
    )


def test_direct_scenes_default_tone_is_neutral(monkeypatch):
    """When the model omits tone, fall back to a neutral default."""
    from lib import visual_director as vd

    monkeypatch.setattr(vd, "_call_openai", lambda *a, **k: (
        '[{"slide_idx": 0, "visual": "matt at desk", "rationale": ""}]'
    ))
    parsed = [("HOOK", "h", "")]
    sd = vd.direct_scenes(parsed_slides=parsed, brand_design="d", api_key="sk-test")
    assert sd.slides[0].tone == "neutral"


def test_direct_scenes_uses_tone_from_llm_response(monkeypatch):
    from lib import visual_director as vd

    monkeypatch.setattr(vd, "_call_openai", lambda *a, **k: (
        '[{"slide_idx": 0, "visual": "matt at desk", "tone": "thoughtful", "rationale": ""}]'
    ))
    parsed = [("HOOK", "h", "")]
    sd = vd.direct_scenes(parsed_slides=parsed, brand_design="d", api_key="sk-test")
    assert sd.slides[0].tone == "thoughtful"


def test_parse_response_content_rejects_tone_over_prompt_cap():
    """Tone parser cap must match the <=20 character prompt contract."""
    from lib import visual_director as vd

    parsed = [("HOOK", "h", "")]
    data = vd._parse_response_content(
        '[{"slide_idx": 0, "visual": "scene", '
        '"tone": "this tone is too long", "rationale": ""}]',
        parsed,
    )
    assert data[0]["tone"] == "neutral"


def test_parse_response_content_sorts_by_slide_idx():
    from lib import visual_director as vd

    parsed = [("HOOK", "h", ""), ("CTA", "c", "")]
    data = vd._parse_response_content(
        '['
        '{"slide_idx": 1, "visual": "cta scene", "rationale": ""},'
        '{"slide_idx": 0, "visual": "hook scene", "rationale": ""}'
        ']',
        parsed,
    )
    assert [entry["visual"] for entry in data] == ["hook scene", "cta scene"]
    assert [entry["slot_role"] for entry in data] == ["HOOK", "CTA"]


def test_parse_response_content_requires_one_entry_per_slide():
    from lib import visual_director as vd

    parsed = [("HOOK", "h", ""), ("CTA", "c", "")]
    import pytest
    with pytest.raises(ValueError, match="one entry per slide"):
        vd._parse_response_content(
            '[{"slide_idx": 0, "visual": "hook scene", "rationale": ""}]',
            parsed,
        )
