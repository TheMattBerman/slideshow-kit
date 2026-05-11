import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "styled-carousel", "scripts"))
import prompt_builder  # type: ignore[reportMissingImports]


SAMPLE_VISUAL = """\
---
brand: test
last-updated: 2026-05-03
---

# Palette
- Background: `#0D1117`
- Primary accent: `#F43F5E`
- Secondary accent: `#FACC15`
- Neutral: `#94A3B8`

# Typography
- Headline weight: extra-bold
- Headline case: UPPERCASE
- Body weight: regular
- Body case: Sentence case
- Pull-quote treatment: italic

# Layout
- Slide arc: HOOK → REVEAL → SETUP → EXAMPLES → OUTCOME → CTA
- Negative space: generous
- Icon style: none

# Vibe Rules
- Tone: minimal
- Avoid: stock photos, gradients, drop shadows

# Output sizes
- LinkedIn carousel: 1024×1536
- Feed: 1024×1024
- Stories: 1024×1792
"""


def test_extracts_palette(tmp_path):
    p = tmp_path / "visual-system.md"
    p.write_text(SAMPLE_VISUAL)
    visual = prompt_builder.parse_visual_system(str(p))
    assert visual["palette"]["background"] == "#0D1117"
    assert visual["palette"]["primary_accent"] == "#F43F5E"


def test_build_hook_prompt_includes_palette_and_text():
    visual = {
        "palette": {"background": "#0D1117", "primary_accent": "#F43F5E", "secondary_accent": "#FACC15", "neutral": "#94A3B8"},
        "typography": {"headline_weight": "extra-bold", "headline_case": "UPPERCASE"},
        "layout": {"negative_space": "generous", "icon_style": "none"},
        "vibe": {"tone": "minimal", "avoid": ["stock photos"]},
    }
    p = prompt_builder.build_hook("I WORK 24 HOURS A DAY", visual, size="1024x1024")
    assert "#0D1117" in p
    assert "I WORK 24 HOURS A DAY" in p
    assert "1024x1024" in p
    assert "minimal" in p.lower()


def test_build_outcome_prompt_uses_secondary_accent():
    visual = {
        "palette": {"background": "#0D1117", "primary_accent": "#F43F5E", "secondary_accent": "#FACC15", "neutral": "#94A3B8"},
        "typography": {"headline_weight": "extra-bold", "headline_case": "UPPERCASE"},
        "layout": {"negative_space": "generous", "icon_style": "none"},
        "vibe": {"tone": "minimal", "avoid": []},
    }
    p = prompt_builder.build_outcome("I WAKE UP WITH LEVERAGE", "LEVERAGE", visual, size="1024x1536")
    assert "#FACC15" in p
    assert "LEVERAGE" in p
