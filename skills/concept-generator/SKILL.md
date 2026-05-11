---
name: concept-generator
description: >
  Generate ranked native social carousel concepts, pick one, draft a script
  with frontmatter compliant with v0.7.0 formats. Produces concepts.md,
  concept-pick.md, script.md, and concept-meta.json for downstream
  styled-carousel rendering. Do NOT use for: image generation, post
  scheduling, or non-carousel content (X threads, X articles, newsletter).
---

# Concept Generator (DNA-Lens)

Three-stage pipeline that replaces the host-agent-freestyle script-generation
gap. Each stage runs as a separate script; chain them via the daily-loop
workflow.

## Pipeline

1. **generate_concepts.sh** -> writes `runs/<date>/concepts.md`
2. **pick_concept.sh** -> writes `runs/<date>/concept-pick.md`
3. **draft_script.sh** -> writes `runs/<date>/script.md` + `concept-meta.json`

## Inputs

- Brand workspace at `<brands_root>/<brand_slug>/` with at minimum a
  `brand-voice.md`. Richer corpora (voice-profile.md, deliverables/recent/)
  produce better output.
- Trend research input from daily-loop Step 4 (markdown file with operator's
  hot takes on selected trends).

## Modes

- `interactive` (default): Stage 3 elicits operator specifics before drafting
  any concept that claims a personal fact. Recommended for own-brand work.
- `autopilot`: Stage 3 never elicits; concepts claiming personal facts are
  down-ranked at Stage 1 so the auto-picker avoids them. Recommended for
  agency / scaled work.

Mode resolves from: `--mode` flag > brand `config.json` `concept_mode` field
> default `interactive`.

## Stage 1: generate_concepts.sh

Loads brand corpus via `lib.concept_corpus.load_brand_corpus`, reads the
trend input, and prompts the host agent (via the `concept_generation`
template in `prompts.json`) to produce N ranked concepts. Each concept has:

- `format` (one of v0.7.0's seven formats)
- `close_action` (save / share / comment / soft)
- `arc` (1-line summary)
- `why_this_works` (3-5 sentences)
- `claims_personal_fact` (true if any concept-level fact requires operator
  confirmation in Stage 3)
- 3-5 `hook_variants`, each with text, pattern (one of six in
  `references/hook-patterns.md`), and 360 shock-score
- `concept_score` (aggregate 0-10)

Output: `runs/<date>/concepts.md` with markdown sections per concept,
ranked top-to-bottom by concept_score.

In autopilot mode, concepts where `claims_personal_fact: true` get a -2
score penalty so the auto-picker avoids them. Operator still sees them.

## Stage 2: pick_concept.sh

In interactive mode, the operator (or upstream agent) provides `--concept N`
to pick the Nth ranked concept. In autopilot mode (no `--concept`), the
script picks the highest-ranked autopilot-safe concept (claims_personal_fact
false). If all concepts claim personal facts in autopilot, the script exits
non-zero with a clear error.

Output: `runs/<date>/concept-pick.md` (a copy of the picked concept's
section + the chosen hook variant; first hook variant by default).

## Stage 3: draft_script.sh

Reads `concept-pick.md`. In interactive mode, if the picked concept has
`claims_personal_fact: true`, prompts the host agent to elicit specifics
from the operator using the `scene_elicitation` template. The agent asks the
minimum questions documented in that template ("Have you actually X?",
"What's your real number / date / situation?"). Operator answers; agent
collects.

Then prompts the host agent (via `script_draft` template) to write the full
script. Format slot template loaded from `lib.format_registry.get_format`;
slide bodies match alias headings.

Pre-output lint chain (any failure aborts):

1. `lib.voice_lint.lint_text` (v0.6.1): em-dash, AI-tell patterns, banned
   words. `--no-lint` bypasses.
2. `lib.format_lint.lint_script_structure` (v0.7.0): slot count, word count,
   close vocab. `--no-format-check` bypasses. Per-style `style.yaml`
   `word_count_override` (v0.8.0) applies when present (set `BRAND_STYLE_DIR`
   env var to point at the brand's style directory).
3. `lib.save_filter.check_save_worthiness` (v0.8.1): heuristic gate (numbers,
   dates, named frameworks, paired quotes, tactical asides) + optional LLM
   fallback. `--no-save-filter` bypasses. Adapts to effective word-cap:
   tight slots (max <=12) need >=1 marker; standard slots (>=13) need
   markers from >=2 categories.

Output: `runs/<date>/script.md` (frontmatter + slot bodies) and
`runs/<date>/concept-meta.json` (data foundation for v0.8.1+ ingestion loop).

**Non-dry-run invocation contract:** the script expects `script.md` to already
be present in `--run-dir` (the host agent writes it after reading the
`script_draft` template + concept-pick.md). draft_script.sh then runs the
3-step lint chain and emits concept-meta.json. Bypass any step with
`--no-lint`, `--no-format-check`, `--no-save-filter`.

## References (one level deep)

- `references/hook-patterns.md`: six hook patterns with exemplars
- `references/concept-patterns/`: kit-shipped concept exemplars (six files)
- `references/carousel-examples/`: operator-supplied annotated carousel
  reference (empty in default install; ingested when Matt provides)
- `references/formats/`: v0.7.0 format YAML files (consumed via
  `lib.format_registry`)

## Authoring a new hook pattern

The six patterns are sufficient per Bug 12. To add a seventh: append an
entry to `lib/hook_patterns.HOOK_PATTERNS` with description, exemplars, and
when_to_use. Mirror in `references/hook-patterns.md`. Tests enforce sync.

## Authoring a new concept pattern

Drop a markdown file in `references/concept-patterns/` matching the existing
shape (Shape / Hook style / Format hint / Body density markers / Close
style / Why it saves / Source exemplars). The skill loads all `*.md` files
in the directory automatically.
