# Execution Evals: slideshow-kit

Behavioral checklist for live runs. Reviewed manually after a live daily loop. Each item has an explicit pass criterion. The smoke harness (`evals/run.py`) covers structural correctness; this doc covers taste and behavior.

## How to use

1. Run the daily loop live for a brand: `SLIDESHOW_BRAND=<slug> ./scripts/run-daily-loop.sh`
2. Open `<brands_root>/<slug>/runs/<today>/`
3. Walk this checklist and mark PASS/FAIL/N/A per item.

Note: stages here collapse logical phases of the daily-loop's Steps 1-9. Mapping is intentionally loose; check items by behavior, not by step number.

## Stage 1: Brand DNA load

- [ ] All three DNA files load without parse errors.
- [ ] Voice principles (3-7) are extracted and rendered in `scripts.md`.
- [ ] Pillars (3-5) are passed to `last30` as input.
- [ ] Visual palette is extracted with all four hex codes.

## Stage 2: Trend fetch

- [ ] `trends.json` exists with at least one trend.
- [ ] Each trend has `id`, `title`, `summary`, at least one `source`.
- [ ] Trend `score` is between 0 and 1.
- [ ] Trends respect `lookback_days` from config.

## Stage 3: Check-in

- [ ] If channel=telegram and bot configured: message lands in Telegram with all 5 trends and timeout note.
- [ ] If channel=agent: prompt renders inline in the agent surface.
- [ ] Telegram failure (test with bad token): loop logs `[WARN]` and proceeds, does NOT crash.
- [ ] Operator reply maps to correct trend index ("3: my take" → trend index 3).
- [ ] Timeout produces autopilot marker in `checkin-response.md`.

## Stage 4: Voice lens application

- [ ] Each generated `scripts.md` section uses voice principles ("lowercase", "ALL CAPS one or two words", etc.) per `brand-voice.md`.
- [ ] No anti-patterns from `brand-voice.md` (LinkedIn-bro hooks, em dashes, generic advice).
- [ ] Hot takes (when present) actually shape the script, not appended as a footer.

## Stage 5: Carousel generation

- [ ] `branded/` folder has 6 PNGs per slide x per configured size.
- [ ] `social-native/` folder has 3-5 PNGs (per format spec) with character continuity.
- [ ] No "Slide X of Y" meta text on any branded slide.
- [ ] Branded slide palette matches `visual-system.md` palette.
- [ ] Social-native carousel is iPhone-real (no glossy lighting, no Canva overlays).

## Stage 6: Publish

- [ ] If mode=draft: posts appear in postiz UI as `draft` status.
- [ ] If mode=autopilot: posts have `scheduled_for` timestamps in postiz UI.
- [ ] `publish-log.json` exists with one entry per post.
- [ ] On postiz failure: telegram alert sent (if configured), exit code 21.

## Stage 7: Run logging

- [ ] `run-summary.json` exists with all expected fields.
- [ ] `runs_history` in `config.json` incremented by 1.
- [ ] All intermediate files (`trends.json`, `checkin-prompt.md`, `checkin-response.md`, `scripts.md`, `prompts.json`, `output-log.json`, `post-*.json`, `publish-log.json`, `run-summary.json`) are present.

## Stage 8: Decoupling (kill-test)

- [ ] Set `TELEGRAM_BOT_TOKEN=invalid` and run: postiz still publishes; loop exits 0.
- [ ] Disconnect a postiz integration and run: telegram still pings; loop exits 21; scripts + images still on disk.
- [ ] Both broken at once: scripts + images on disk, exit 21, no telegram, no postiz, but run-summary.json captures both failures.

## Pass criteria

A daily run "passes execution evals" if every item above is PASS or N/A. One FAIL means the loop needs work before going to autopilot for that brand.
