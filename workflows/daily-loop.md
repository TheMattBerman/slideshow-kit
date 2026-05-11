# Workflow: Daily Loop

> **Audience:** the host agent (Claude Code, Codex, OpenClaw, Hermes). Not user-invocable. Triggered by cron or by the user saying "run today's slideshow loop for <brand>".

End-to-end orchestrator: trends → check-in → brand DNA lens → carousels → publish → log. Composes external skills (`last30`) and internal skills (`styled-carousel`) via the host's skill mechanism. Telegram and postiz are independent failure domains.

## Inputs

- `--brand <slug>` flag (preferred)
- `$SLIDESHOW_BRAND` env var (fallback)
- `default_brand` in `~/.clawd/slideshow-kit/config.json` (last resort)

If none resolve: error `no brand resolved: pass --brand or set a default`.

## Step 1: Resolve brand and load DNA

1. Determine `BRAND_SLUG` from inputs above.
2. `BRAND_DIR=$SLIDESHOW_BRANDS_ROOT/$BRAND_SLUG`. Verify it exists.
3. Read three DNA files:
   - `$BRAND_DIR/brand-voice.md`
   - `$BRAND_DIR/brand-perspective.md`
   - `$BRAND_DIR/visual-system.md`
4. Read `$BRAND_DIR/config.json` and capture: `mode`, `lookback_days`, `posts_per_day`, `formats`, `checkin`, `postiz`, `runs_history`.
5. Compute `TODAY=$(date +%Y-%m-%d)` and `RUNS_DIR=$BRAND_DIR/runs/$TODAY`. Create it.

## Step 2: Live-spend gate

Read `references/live-spend-gating.md`. Apply the rule:

- If `mode == "autopilot"` AND `runs_history < 7`:
  - **Refuse** with: `[FAIL] brand <slug> is in autopilot with only <N> runs of history. Required: 7. Run in draft mode for <7-N> more days, or flip to draft in config.json. See references/live-spend-gating.md.`
  - Exit non-zero. Do not invoke last30, do not call gpt-image-2, do not call postiz.

If gate passes, continue.

## Step 3: Invoke `last30` skill

Use the host's skill-invocation mechanism (do NOT shell out). The exact API depends on host:

- Claude Code / Codex: invoke `last30` (or `last30days`) with `pillars` (extracted from `brand-perspective.md` § Pillars) and `lookback_days` (from `config.json`).
- OpenClaw: same, via `openclaw skills run last30 ...`.
- Hermes: via the Hermes skill router.

Capture the skill output to `$RUNS_DIR/trends.json`. Expected schema (the kit's evals fixture documents this):

```json
{
  "generated_at": "<ISO>",
  "lookback_days": 7,
  "pillars": ["..."],
  "trends": [
    {"id": "t-001", "title": "...", "summary": "...", "sources": [...], "score": 0.92},
    ...
  ]
}
```

If `trends` is empty, log `[INFO] no trends today; skipping`. Append a `runs_history` increment to `config.json` and exit 0.

## Step 4: Run check-in

Invoke `workflows/checkin.md` (read it, follow it). Inputs: `brand_slug`, `trends_path=$RUNS_DIR/trends.json`, `runs_dir=$RUNS_DIR`.

Output: a hot-takes dict `{trend_index: take_text}` (possibly empty for autopilot). Persist to `$RUNS_DIR/checkin-response.md` (the check-in workflow handles this).

Telegram failure here MUST NOT block the rest of the loop (decoupling rule).

## Step 5: Generate concepts, pick, and draft script

The concept-generator skill (v0.8.0) replaces the operator-writes-script
flow with a three-stage pipeline. Operators who prefer to hand-write scripts
can skip Step 5 and go directly to Step 6 with their own script.md.

### Step 5a: Generate ranked concepts

```
./skills/concept-generator/scripts/generate_concepts.sh \
  --brand $BRAND \
  --trend-input $RUNS_DIR/checkin-response.md \
  --output $RUNS_DIR/ \
  --mode $CONCEPT_MODE
```

The host agent reads `prompts.json`'s `concept_generation` template plus
the context bundle and writes `$RUNS_DIR/concepts.md` with N ranked concepts.
Each concept includes a one-line `visual_hook` (a v0.8.0 amendment) so the
operator can compare visually as well as textually.

### Step 5b: Pick a concept

Interactive:
```
./skills/concept-generator/scripts/pick_concept.sh \
  --run-dir $RUNS_DIR --concept N
```

Autopilot:
```
./skills/concept-generator/scripts/pick_concept.sh \
  --run-dir $RUNS_DIR --mode autopilot
```

Output: `concept-pick.md`.

### Step 5c: Draft the script + scene direction

```
./skills/concept-generator/scripts/draft_script.sh \
  --run-dir $RUNS_DIR \
  --mode $CONCEPT_MODE
```

In interactive mode with a personal-fact-claiming concept, the host agent
elicits operator specifics via `prompts.json`'s `scene_elicitation` template
before drafting. Otherwise, the agent uses the picked concept and corpus to
draft directly.

**Invocation contract:** the host agent must write `script.md` to `--run-dir`
BEFORE calling `draft_script.sh` in non-dry-run mode. The script then runs
the lint chain on that file and emits `concept-meta.json`. Use `--dry-run` to
emit a placeholder script.md instead (useful for scaffold/testing).

The lint chain runs pre-output: voice-lint (v0.6.1), format-lint (v0.7.0)
with style.yaml `word_count_override` merged when present, save-filter
(v0.8.0). Bypass any with `--no-lint`, `--no-format-check`, `--no-save-filter`.

After lint, Stage 3 calls `lib.visual_director.direct_scenes` to produce
per-slide scene briefs and writes `scene-direction.md`. Visual decision
happens at script-write time so the visual matches the story.

Output: `script.md` + `concept-meta.json` (schema_version 2) + `scene-direction.md`.

### Step 5d: Operator review (optional in interactive)

Operator reads `script.md` AND `scene-direction.md` before Step 6. Edits in
place if needed. Step 6 re-runs voice-lint + format-lint at invocation time,
so script edits get re-validated. scene-direction.md edits are honored
verbatim by Step 6 (renderer reads it as-is).

If `scene-direction.md` is missing (you skipped concept-generator and
hand-wrote script.md), styled-carousel calls `direct_scenes` lazily at render
time with no visual_hook and writes scene-direction.md before rendering. Your
visuals still match the script; you lose the concept-stage visual through-line.

## Step 6: Generate carousels (style-driven)

Read `config.styles_per_day` (array of style names; defaults to `[default_style]`).
For each style in `styles_per_day`, for each script:

- Invoke the host's skill mechanism on `styled-carousel`. Pass:
  - `--brand $BRAND_SLUG`
  - `--style <style-name>`
  - `--script <script-path>`
  - `--output $RUNS_DIR/`

Output for each (slide x size) lands at `$RUNS_DIR/<style>-slide-NN-<dims>.png`.
Plus `prompts.json` and `output-log.json` per skill spec.

Style resolution at runtime (within the skill):

1. `--style <name>` flag (per-run override)
2. Brand's `default_style` from `config.json`
3. Kit default: `social_native` (from `references/styles/social_native/`)

Token inheritance: kit defaults <- brand `visual-system.md` (DESIGN.md-shaped) <- style `DESIGN.md`.

Image-generation cost is gated per-skill by brand `mode` (live-spend gate from Step 2).

## Step 7: Build post payloads

For each generated carousel, write a `post-NN.json` to `$RUNS_DIR/`:

```json
{
  "caption": "<from script.HOOK + first line of script.OUTCOME, see brand-voice.md length rules>",
  "images": ["dickie_bush_narrative-slide-01-1080x1350.png", "..."],
  "platforms": ["linkedin", "instagram"],
  "scheduled_for": "<ISO timestamp, optional>"
}
```

`scheduled_for` is optional but honored when set. As of v0.5.0 the postiz wrapper passes a present-and-valid `scheduled_for` (ISO-8601 UTC, ending in `Z`) through as `-s` in both draft and autopilot modes; if it is absent or malformed, the wrapper falls back to `now+5min`. Host agents may set it in either mode (e.g. to time-of-day-shift a draft for review-then-publish).

## Step 8: Publish via postiz

Invoke:

```bash
./scripts/publish_postiz.sh \
  --brand $BRAND_SLUG \
  --posts $RUNS_DIR/ \
  --mode $(grep -o '"mode":[^,}]*' "$BRAND_DIR/config.json" | head -n1 | sed 's/.*"mode"://; s/[" ]//g')
```

- `mode == "draft"` (default): postiz creates draft posts in the postiz UI. Operator approves manually.
- `mode == "autopilot"`: postiz schedules the post. The wrapper uses `scheduled_for` from `post-NN.json` if present and valid, otherwise `now+5min`.

Capture exit code:
- **0**: log success.
- **21** (postiz failure): save scripts + images locally (already done), send a Telegram alert if available (`./scripts/send_telegram.sh ... --text "[brand] postiz failed: see <RUNS_DIR>/publish-log.json"`), exit non-zero so cron surfaces the failure.

## Step 9: Log the run

Update `$BRAND_DIR/config.json`: increment `runs_history` by 1.

Write `$RUNS_DIR/run-summary.json`:

```json
{
  "brand": "<slug>",
  "date": "<YYYY-MM-DD>",
  "trends_count": <int>,
  "checkin_status": "responded|autopilot|telegram_failed",
  "carousels_generated": <int>,
  "publish_mode": "draft|autopilot",
  "publish_status": "ok|partial|failed",
  "duration_seconds": <int>
}
```

## Decoupling guarantees (recap)

- Telegram failure → autopilot for that day, postiz still runs.
- Postiz failure → run logs persist, Telegram alert sent if available, exit non-zero so the operator knows.
- Image-gen failure on one slide → the skill itself decides whether to retry or fail the whole carousel; daily loop captures and proceeds with what was generated, then exits non-zero.

## Cron example

Single brand, daily at 09:00 local:

```cron
0 9 * * * cd ~/Documents/GitHub/slideshow-kit && SLIDESHOW_BRAND=matt ./scripts/run-daily-loop.sh >> <brands_root>/matt/runs/cron.log 2>&1
```

Multi-brand (agency, daily 09:00):

```cron
0 9 * * * cd ~/Documents/GitHub/slideshow-kit && for b in $(./scripts/list_brands.sh | awk '{print $1}'); do SLIDESHOW_BRAND=$b ./scripts/run-daily-loop.sh; done
```

(`scripts/run-daily-loop.sh` is the host-specific wrapper that invokes this markdown workflow against the host's agent CLI. The kit ships only the workflow markdown; the wrapper is host-specific and lives in the user's dotfiles.)
