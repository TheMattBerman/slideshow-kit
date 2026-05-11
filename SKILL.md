---
name: slideshow-kit
description: "Daily brand-DNA-driven social autopilot kit. Use when the user wants to generate branded or social-native carousels for LinkedIn, Instagram, TikTok, X, or Threads from a brand's voice, perspective, and visual system. Triggers on requests like 'generate a carousel', 'make slides for [brand]', 'turn this trend into a post', 'run my daily content loop', or 'onboard a new brand'. Do NOT use for: writing single tweets or LinkedIn posts (use matt-linkedin or x-thread skills), generating ads (use ad-creative or stealads), or any task that doesn't involve multi-slide carousel output."
metadata:
  openclaw:
    emoji: "📱"
    user-invocable: true
    primaryEnv: "claude-code,codex,openclaw,hermes"
    requires:
      - last30
---

# Slideshow Kit

Top-level router. Dispatches to subskills and workflows based on user intent.

## When the user asks for a carousel

If they have a brand workspace at `<brands_root>/<slug>/` (default `./brands/`, see references/brand-management.md):
- List available styles with `scripts/list_styles.sh <slug>` when the style is
  ambiguous or the user asks for a look that is not already defined.
- If no suitable style exists, ask the user to describe the reusable style and
  whether they have visual examples. Then follow `references/style-system.md`
  to create `<brand>/styles/<style-name>/DESIGN.md` and optional refs before
  rendering.
- Brand-aligned, social-native, and thread/native text looks all route through
  `skills/styled-carousel/` with the selected `--style`.

If they don't have a brand workspace yet:
- Read `workflows/onboard-brand.md` and walk the user through paste mode (default) or interview mode
- The workflow runs `scripts/init_brand.sh <slug>` itself, then extracts brand DNA from samples or 12 questions
- After completion, all three DNA files plus reusable style(s) are present at `<brands_root>/<slug>/`; a default character is also present when a social-native/candid-person style is selected.

## When the user asks to run the daily loop

(v0.3.0+) Read `workflows/daily-loop.md` and walk the steps.

## When the user asks about brands

- Create new: `scripts/init_brand.sh <slug>`
- List existing: `scripts/list_brands.sh`
- Switch default: `scripts/switch_brand.sh <slug>`
- Create or refine a visual style: follow the natural-language flow in `references/style-system.md`; use `scripts/add_style.sh` only as the internal implementation detail.
- Multi-brand model: see `references/brand-management.md`

## Brand DNA contract

Every brand has three files at `<brands_root>/<slug>/`:
- `brand-voice.md` — how the brand talks
- `brand-perspective.md` — what it believes (pillars, hot takes, ICP)
- `visual-system.md` — palette, typography, layout, output sizes

Subskills and workflows read these directly. Never duplicate or vendor brand state inside the kit.
