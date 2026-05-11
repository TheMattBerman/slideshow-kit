# Changelog

Release notes moved out of `README.md` so the README can explain what the kit is, why it exists, and how to run it.

## v0.8.1 - Cleanup + save_filter wired

Patch release. No new features. Closes the deferred reviewer findings from the v0.8.0 ship.

- `save_filter` now runs in Stage 3. v0.8.0 shipped the lib but had not wired it into `draft_script.sh`. `--no-save-filter` bypasses. The lint chain is now genuinely three-step: voice_lint -> format_lint -> save_filter.
- Narrowed exception scope in save_filter LLM-callback. Auth/quota/SSL errors now log to stderr instead of silently falling through; bugs in the user-supplied callback also surface loudly.
- `SCENE_DIRECTION_SOURCES` is a single source of truth in `lib/visual_director.py`; `lib/concept_meta.py` imports it.
- `_script_hash` includes `slot_role` to prevent role-swap cache poisoning.
- `is_thin` cleaned up in `lib/concept_corpus.py`. Brands with a real `brand-voice.md` but no `voice-profile.md` are no longer flagged as thin.
- Magic numbers promoted to module constants (`TIGHT_SLOT_WORD_CAP_MAX`, `SNIPPET_TRUNCATION_LENGTH`, `DIRECT_SCENES_PROMPT_CAP`, `DIRECT_SCENES_CONTEXT_FIELD_CAP`).
- `generate_visuals` + `SlideVisual` deleted after the v0.8.0 `direct_scenes` shared-primitive refactor.
- `draft_script.sh` heredoc promoted to `lib/draft_script_meta.py` for unit-testability.
- 256KB cap on `--trend-input` in `generate_concepts.sh` prevents OOM on adversarial input.
- Honest `tone` field via LLM JSON output. The v0.8.0 always-neutral holding pattern is replaced; the LLM now emits a tone label per scene, with `"neutral"` as the parser default when omitted.

Operator action: none. v0.8.0 scripts continue to work.

Test growth: 255 pytest -> 264 pytest. 127 bats -> 129 bats.

## v0.8.0 - Concept generator + visual integration

New skill: `skills/concept-generator/`. Three-stage pipeline that replaces the host-agent-freestyle script-generation gap.

```text
generate_concepts.sh -> pick_concept.sh -> draft_script.sh
```

Stage outputs land in the run dir:

- `concepts.md`
- `concept-pick.md`
- `script.md`
- `scene-direction.md`
- `concept-meta.json`

Highlights:

- Brand corpus loader `lib/concept_corpus.py` walks well-known paths (`voice-profile.md`, `brand-voice.md`, `deliverables/recent/`) with built-in defaults.
- Six-pattern hook primitive with 360 shock-score baked in.
- Save filter (`lib/save_filter.py`) adds a heuristic gate plus optional LLM fallback.
- Two operator modes: `interactive` and `autopilot`.
- Concept patterns ship in `references/concept-patterns/`.

### Visual Integration

The visual decision moves to script-write time so the visual matches the story by construction.

- `visual_hook` is now part of every concept in `concepts.md`.
- `lib/visual_director.direct_scenes` is a shared primitive callable from Stage 3 and styled-carousel fallback.
- styled-carousel renderer reads `scene-direction.md` if present; otherwise calls `direct_scenes` lazily.
- Per-style word-cap override via `brands/<slug>/styles/<style>/style.yaml`.
- Agent-prompt size cap: every prompt in `skills/concept-generator/prompts.json` capped at 2000 chars.
- `concept-meta.json` schema bumps 1 -> 2 with `visual_hook`, `scene_direction_source`, `word_cap_overridden`, and `word_cap_source_path`.

Operator action: none required for the kit. Operators who want tighter character-driven word caps should drop a `style.yaml` next to the style's `DESIGN.md`.

## v0.7.6 - Render resilience

When OpenAI's API was slow or transient errors hit a single slide, the kit previously aborted the whole render mid-loop, leaving partial PNGs on disk without `prompts.json` or `output-log.json`.

v0.7.6 makes per-slide rendering resilient:

- Per-slide failures are caught, logged into a new `slide_results` array in `output-log.json`, and the loop continues.
- `prompts.json` and `output-log.json` are always written, even on partial render.
- `output-log.json` adds `slides_completed`, `slides_failed`, and `slide_results`.
- The curl `--max-time` ceiling on `/edits` calls bumps from 360s to 600s.
- Exit code is 0 only when all slides succeed; 1 if any failed, with a `[PARTIAL]` summary.

Operator action: none. The new fields are additive.

## v0.7.5 - Prompt slim

The v0.7.4 character-driven `social_native` rendered with multi-ref input locked likeness and unlocked scene variety, but captions still mostly failed. The prompt was too long and buried the exact text instruction.

v0.7.5 ships a slim prompt for `iphone_candid` styles:

- Drops the YAML token dump.
- Drops the `DESIGN.md` body verbatim.
- Replaces rigid lower-third caption language with cleaner typography guidance.
- Strengthens the no-paraphrase clause: "Do not paraphrase, abbreviate, or summarize the text. Render every word."

Operator action: none required.

## v0.7.4 - Visual director

The v0.7.3 character-driven `social_native` rendered Matt's likeness and text correctly but produced visually monotonous carousels. v0.7.4 adds a visual director: a small LLM call that reads the parsed script, the brand's character profile, and brand voice, then produces one specific visual directive per slide.

Also fixed: v0.7.3's auto-truncation was making slide 1 paraphrase its caption because the trailing ellipsis signaled incomplete text. Auto-truncation is gone in v0.7.4.

Operator action: none required for non-character-driven styles. For character-driven styles, the visual director runs automatically when `OPENAI_API_KEY` is set. Skip with `--no-visual-director`.

Cost: one `gpt-4o-mini` call per render, about $0.001 per carousel.

Deferred to v0.8.0: moving per-slide directive generation into the broader concept-generator skill.

## v0.7.3 - Exact-text rendering + caption truncation

A real-world render exposed two problems with v0.7.2's `iphone_candid` framing: `gpt-image-2` paraphrased or dropped body text, and long body text caused the model to bail out.

Fixed via two coupled changes:

- `iphone_candid` framing now uses a literal quoted exact-text instruction and "do not paraphrase" clauses.
- Caption text is hard-truncated at 60 characters for `iphone_candid` styles only, with a warning to stderr.

Operator action: captions over 60 chars now get auto-truncated. Either pre-shorten copy or accept truncation.

Deferred to v0.8.0: batched multi-slide generation and multi-reference input.

## v0.7.2 - Style-aware prompt framing

v0.7.2 makes `compose_prompt` style-aware. The framing paragraph resolves from the style's `image_treatment` token at render time:

| `image_treatment` | Framing |
|---|---|
| `screenshot_native` | Typography is the design; do not illustrate the words |
| `iphone_candid` | Character photo is the base; render slide text as a caption overlay |

Unknown or missing `image_treatment` falls back to `screenshot_native`.

Operator action: none required.

## v0.7.1 - Hotfix

Bug fixes:

- SSL cert verify auto-recovery. `gpt_image_2` now falls back to `certifi` when the system SSL bundle fails verification.
- Slide body text no longer rendered as imagery. `compose_prompt` wraps slide text in explicit typography framing.

New: `thread_native` style.

- Added `references/styles/thread_native/` with the type-forward Twitter-thread / notes-app aesthetic.

Operator action: none required.

## v0.7.0 - Format pluggability + carousel structure

Seven first-class carousel formats:

| Format | Use case |
|---|---|
| `narrative` | Story-driven case studies |
| `numbered_diagnostic` | "The N tells", "5 reasons your X is broken" |
| `receipt_context` | Quote-then-react |
| `process_reveal` | "How I did X in N minutes" |
| `anatomy_breakdown` | Teardowns |
| `before_after` | Transformations |
| `counter_narrative` | Contrarian frame on industry orthodoxy |

Carousel structure rules at lint time:

- Per-slot word count ranges.
- Slot count ranges.
- CTA-on-visual close slide vocabulary.

Brand close-vocab override added through `## Close vocabulary` in `brands/<slug>/brand-voice.md`.

Backward compatibility: v0.6.x scripts with no frontmatter parse as `format: narrative, close_action: save`.

## v0.6.1 - Hotfix + lint foundation

Bug fixes:

- Brand visual-system tokens now merge correctly.
- One-shot converter detects prose-shaped or hybrid visual systems:

```bash
./scripts/migrate_brand_visual_system.sh --brand <slug>
```

New voice lint primitive:

- `lib/voice_lint.py` enforces no-em-dash, no-AI-tell-pattern, and no-engineering-jargon rules.
- Call sites: styled-carousel pre-render hook, standalone `scripts/lint_script.sh`, and `doctor.sh` brand-voice scan.
- Brand-specific rules live in a `## Avoid` section.

Observability:

- Every styled-carousel run writes `<run_dir>/resolved-tokens.json` with layer provenance.

Prompt diet:

- Per-slide prompt leads with slide intent.
- Style meta-guidance is stripped before composition.

## v0.6.0 - The style system

- One unified `styled-carousel` skill replaces `branded-carousel` and `social-native-carousel`.
- Each brand has a `styles/` directory of named, persistent visual recipes.
- Token inheritance: kit default -> brand `visual-system.md` -> style `DESIGN.md`.
- New scripts: `add_style.sh`, `list_styles.sh`.
- See `references/style-system.md`.

Breaking changes:

- `branded-carousel` skill renamed to `styled-carousel`.
- `social-native-carousel` skill removed; its pattern lives as `references/styles/social_native/`.
- Config schema: `formats` field is no longer read; `default_style` and `styles_per_day` replace it.
- Existing brand workspaces require re-running `init_brand.sh --force`.

## v0.5.0

- Postiz `--media` upload step: per-image `postiz upload`, then comma-joined URLs into `posts:create -m`.
- `scheduled_for` in `post-NN.json` honored in draft and autopilot modes when present and ISO-8601 UTC.

## v0.4.0

- Daily-loop orchestrator: trends -> check-in -> brand DNA lens -> carousels -> Postiz publish -> run log.
- Check-in workflow with Telegram or in-session agent surface.
- `scripts/send_telegram.sh`: curl wrapper around Telegram Bot API.
- `scripts/publish_postiz.sh`: Postiz CLI wrapper with `--dry-run`.
- Live-spend gating: every brand defaults to `mode: "draft"`; autopilot requires 7+ runs of history.
- Telegram and Postiz are independent failure domains.

## v0.3.0

- Recurring-character continuity solved with `--mode` flag on `social-native-carousel`.
- Auto face-similarity quality gate using `gpt-4o-mini` vision.
- Per-brand `snc_mode` override.
- Caption-position lock.
- Character bible reference doc.

## v0.2.0

- Cross-agent skill installation for Claude Code, Codex, OpenClaw, and Hermes.
- Multi-brand workspace management.
- `branded-carousel` skill.
- `social-native-carousel` skill.
- `workflows/onboard-brand.md` for paste-mode and interview-mode brand DNA extraction.
- `gpt-image-2` image generation with save-first error handling.
- Three platform sizes per slide.
