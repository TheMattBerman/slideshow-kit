# Skill Composition

When the daily loop calls which skill, and why. Read this if you're modifying `workflows/daily-loop.md` or adding a new format.

## The three composing skills

1. **`last30`** — external (lives in the user's skill kit, not slideshow-kit). Pulls trends from Reddit, X, YouTube, TikTok, Instagram, Hacker News, etc.
2. **`branded-carousel`** — internal (slideshow-kit subskill). Generates 6-slide carousels with the brand's locked visual identity (palette, type, layout from `visual-system.md`).
3. **`social-native-carousel`** — internal (slideshow-kit subskill). Generates iPhone-real candid carousels with character continuity. Reads `brand-voice.md` and visual cues from `visual-system.md` (vibe rules, not strict palette).

## Invocation pattern

The daily loop is itself a skill-kit. It composes other skills via the **host agent's skill-invocation mechanism**, not via shell wrappers. Rationale (per spec §7.4):

- A wrapper script wouldn't be portable across hosts.
- Each host (Claude Code, Codex, OpenClaw, Hermes) has its own invocation API.
- Agents already know how to invoke skills — let the host do what it's designed to do.

The two exceptions where the kit DOES shell out:
- `scripts/send_telegram.sh` — pure curl, deterministic, no agent judgment needed.
- `scripts/publish_postiz.sh` — wraps a CLI binary, deterministic, no agent judgment needed.

## Decision tree — which carousel skill?

The daily loop reads `config.json` field `formats`:

```
formats: ["branded"]                      → branded-carousel only
formats: ["social-native"]                → social-native-carousel only
formats: ["branded", "social-native"]     → BOTH (two posts per trend)
formats: []                               → error: no format configured
```

When BOTH are configured, the daily loop creates two `post-NN.json` files per trend — one branded, one social-native — and postiz schedules them as separate posts.

## Why not auto-pick?

Auto-picking the format based on the trend's vibe is tempting and wrong. The brand's perspective and visual system anchor each format; the operator decides which formats fit their feed strategy. Auto-pick was rejected in spec §3.

## Format guidance (for operators editing config.json)

| Brand profile | Recommended formats |
|---|---|
| Strong visual identity, B2B, LinkedIn-first | `["branded"]` |
| Personal brand, X/Threads-first, candid voice | `["social-native"]` |
| Both audiences (most agencies) | `["branded", "social-native"]` |
| Stories/Reels-only motion-first brand | `["branded"]` with stories sizes (motion is v1.1) |

## When to add a new format (future)

Future formats (e.g. `["video-shorts"]`, `["meme"]`) would slot in as new sub-skills under `skills/`. The daily loop would route on the same `formats` list. No changes to `last30` or check-in needed.

## Test-time composition

For evals (`evals/run.py`), composition is replaced with fixtures:
- Fixture trends.json instead of `last30`
- Fixture brand DNA instead of real `<brands_root>/<slug>/`
- Dry-run carousel script construction (text only, no image gen)
- Dry-run postiz publish (no CLI call)

This keeps the eval offline and free.
