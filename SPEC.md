# Slideshow Kit — Spec

Technical contract for inputs, outputs, and validation rules.

## Brand DNA contract

Three required files per brand at `<brands_root>/<slug>/`:

### brand-voice.md
- YAML frontmatter: `brand`, `extracted-from` (paste|interview|hybrid|manual), `extracted-on` (YYYY-MM-DD), `sample-count` (int)
- Markdown sections (all required): `# Voice Principles`, `# Structure`, `# Signature Patterns`, `# What NOT to Do`, `# Length / Format`

### brand-perspective.md
- YAML frontmatter: `brand`, `extracted-from`, `last-updated` (YYYY-MM-DD)
- Markdown sections (all required): `# ICP`, `# Pillars`, `# Hot Takes`, `# Things We Don't Talk About`, `# Trend Filters`

### visual-system.md
- YAML frontmatter: `brand`, `last-updated`
- Markdown sections (all required): `# Palette`, `# Typography`, `# Layout`, `# Vibe Rules`, `# Output sizes`

Validators in `tests/test_validate_brand.py` check presence of all required sections and frontmatter keys.

## Brand workspace contract

`<brands_root>/<slug>/`:
- `brand-voice.md` (required)
- `brand-perspective.md` (required)
- `visual-system.md` (required)
- `config.json` (auto-created by init_brand.sh — postiz integration ids, telegram chat_id, mode, lookback_days)
- `runs/<YYYY-MM-DD>/` (created per daily run)

### config.json schema

`<brands_root>/<slug>/config.json` is auto-created by `init_brand.sh` and may include:

- `postiz` (object) — Postiz integration ids
- `telegram_chat_id` (string) — Telegram channel id for daily-loop check-ins
- `mode` (`paste` | `interview` | `hybrid` | `manual`) — onboarding mode used
- `lookback_days` (int) — daily-loop trend lookback window
- `snc_mode` (`per-slide` | `batch` | `anchor-chain`) — overrides the social-native-carousel default. When set, `--mode` resolution becomes: explicit flag > `snc_mode` > kit default (`anchor-chain`).

## Carousel skill contract

Inputs:
- `--brand <slug>` (required)
- `--script <path>` (markdown with HOOK, REVEAL, SETUP, EXAMPLES[], OUTCOME, CTA sections)
- `--output <dir>` (default `<brands_root>/<slug>/runs/<date>/`)
- `--sizes <list>` (default reads from visual-system.md `# Output sizes`)
- `--dry-run` (no API spend; emit prompts only)

Outputs:
- One PNG per slide per size (filename: `slide-<NN>-<size>.png`)
- `prompts.json` — exact prompts used per slide
- `output-log.json` — generation metadata (timestamps, model, sizes, cost estimate)

## Cross-agent install contract

`install.sh` succeeds when at least one agent path is detected. Targets:
- `~/.claude/skills/`
- `~/.codex/skills/`
- OpenClaw config dir (`~/.clawd/skills/` or `$OPENCLAW_HOME/skills/`)
- Hermes plugin dir (`$HERMES_PLUGIN_PATH` if set)

If zero detected, prints a clear error and exits 1.

## Doctor contract

`doctor.sh` exits 0 if all checks PASS or WARN, exits 1 if any check FAILs. Output format: one line per check, prefix `[PASS]`, `[WARN]`, or `[FAIL]`.

## Face-similarity contract

Every non-dry-run carousel run with `--score-faces` (default on) writes `face-similarity.json` to the output directory.

Schema:

```json
{
  "skipped": false,
  "slide_count": 5,
  "mean_score": 0.890,
  "threshold": 0.75,
  "passes": true,
  "pairs": [
    {"a": "slide-01-pain-opener-1024x1024.png",
     "b": "slide-02-lived-detail-1024x1024.png",
     "score": 0.90}
  ]
}
```

When skipped (no `OPENAI_API_KEY` available):

```json
{
  "skipped": true,
  "reason": "OPENAI_API_KEY not set",
  "slide_count": 5
}
```

Implementation: pure-Python pairwise comparison, OpenAI gpt-4o-mini vision via curl subprocess. No numpy. Module: `skills/social-native-carousel/scripts/score_face_similarity.py`. The `mean_score` is the simple arithmetic mean of all C(n,2) `pairs[*].score` values for n>=2 slides; `null` for runs with fewer than 2 slides. The `passes` field is `mean_score >= threshold` or `True` when `mean_score is null`.
