# Live-Spend Gating

The kit can spend real money — gpt-image-2 image generation, postiz scheduled publishing, Telegram bot quota. Live-spend gating exists so a misconfigured brand can't burn down a credit card on day one.

## The hard rules (from spec §9)

1. **Every new brand defaults to `mode: "draft"`** in its `config.json`. Set by `scripts/init_brand.sh` — not configurable at scaffold time.
2. **`mode` flips to `"autopilot"` only by explicit user edit** of `<brands_root>/<slug>/config.json`. The kit never writes `"autopilot"` automatically.
3. **`autopilot` is gated on `runs_history >= 7`.** The daily loop refuses to run in autopilot mode for any brand with fewer than 7 historical runs. Operators must accumulate 7 days of draft-reviewed output before flipping the switch.
4. **All image-gen scripts default to `--dry-run`** when invoked standalone. The daily loop does not pass `--dry-run`, but standalone use of the carousel skills requires `--confirm-spend` to actually call gpt-image-2.
5. **`doctor.sh` warns** when any brand is in autopilot mode with `runs_history < 7`. Exit code stays 0 (warn, not fail), but the operator sees it on every health check.

## The rationale

- **Draft-first builds taste before scale.** The first 7 days of any brand are the noisiest — voice extraction is rough, perspective filters miss, visual-system bugs are unpatched. Drafts force human review until the loop is dialed.
- **One bad config can't drain the API budget.** A typo'd `mode` or copy-pasted `integration_ids` would otherwise schedule garbage to a real LinkedIn page. The 7-day floor forces real eyes on real output before automation.
- **Telegram alerts work even when postiz fails.** Live spend on postiz can fail; the operator finds out via Telegram. The decoupling rule (spec §7.3) plus the live-spend gate together make the system safe to leave running.

## Where the gate lives in code

- `workflows/daily-loop.md` Step 2: refuses to run if `mode == "autopilot" && runs_history < 7`.
- `doctor.sh`: WARN line per-brand when same condition is true.
- `skills/branded-carousel/scripts/generate_branded_carousel.py`: defaults `--dry-run` unless `--confirm-spend` is passed; daily-loop invocation passes `--confirm-spend` based on brand mode.
- `skills/social-native-carousel/scripts/generate_social_native_carousel.py`: same pattern (Plan 2 deliverable).

## Flipping a brand to autopilot

After at least 7 successful draft runs:

```bash
# 1. Confirm runs_history (stdlib parse — no jq runtime dep)
grep -o '"runs_history":[0-9]*' <brands_root>/<slug>/config.json
# expect: 7 or higher

# 2. Edit config.json
$EDITOR <brands_root>/<slug>/config.json
# change "mode": "draft" to "mode": "autopilot"

# 3. Verify with doctor
./doctor.sh
# expect: PASS for that brand, no autopilot warning
```

If you flip to autopilot and runs_history is < 7, the next daily-loop run will refuse and exit non-zero with a clear message.

## Override (intentional risk)

There is no override flag. If you want to autopilot before 7 runs, you must accumulate the run history first — either by running 7 real days in draft, or by manually incrementing `runs_history` in `config.json`. Manual increment is your foot, your bullet.

## What "draft" actually does

`mode: "draft"` makes `publish_postiz.sh` invoke `postiz posts:create -t draft` (postiz CLI v2.0.13). Posts land in the postiz UI, status `draft`, awaiting human approve-and-publish. No external publishing happens. Image-gen still spends gpt-image-2 quota — the gate is on publishing, not on generation.

If you want to dry-run gpt-image-2 too, pass `--dry-run` to the daily-loop's image-gen step (or run the standalone skills with `--dry-run`).
