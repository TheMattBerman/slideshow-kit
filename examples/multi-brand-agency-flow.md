# Example: Multi-brand Agency Flow

Three brands, one cron, one operator. This walkthrough shows how an agency runs slideshow-kit for `acme`, `widget-co`, and `the-pet-pantry` from a single machine.

## Setup (one-time)

```bash
# Each brand gets its own workspace
./scripts/init_brand.sh acme
./scripts/init_brand.sh widget-co
./scripts/init_brand.sh the-pet-pantry

# Onboard each one (Plan 2 workflow). For each:
$EDITOR <brands_root>/acme/brand-voice.md
$EDITOR <brands_root>/acme/brand-perspective.md
$EDITOR <brands_root>/acme/visual-system.md
# repeat for widget-co, the-pet-pantry

# Wire postiz integrations per brand
postiz integrations list
# Copy each brand's relevant ids into <brands_root>/<slug>/config.json

# Wire telegram per brand (each brand has its own group chat)
# See references/telegram-setup.md
```

After setup:

```bash
./scripts/list_brands.sh
# acme
# widget-co
# the-pet-pantry (default)
```

## Daily ops

> Note: `run-daily-loop.sh` is the operator-provided host wrapper that invokes the daily-loop workflow against your agent CLI. The kit ships the workflow markdown only; you author the wrapper for your host. See `workflows/daily-loop.md` for the wrapper contract.

### Single cron, sequential brands

```cron
# crontab
0 9 * * * cd ~/Documents/GitHub/slideshow-kit && for b in acme widget-co the-pet-pantry; do SLIDESHOW_BRAND=$b ./scripts/run-daily-loop.sh; done >> ~/.clawd/agency-cron.log 2>&1
```

What happens at 9am:

```
9:00:00  start acme
         → last30 fetch (3 trends)
         → telegram check-in to #acme-team
         → operator replies "1: agree, 3: lean harder"
         → branded-carousel produces 6 slides × 2 sizes
         → postiz drafts 1 post (draft mode, day 4 of 7)
         → run logged
9:08:00  start widget-co
         → last30 fetch (5 trends)
         → telegram check-in to #widget-co-team. no reply, autopilot at 9:38
         (But other brands keep running: this is sequential not blocked)
         (Day 12: autopilot mode active)
         → branded + social-native carousels (12 slides total)
         → postiz schedules at 11:00, 14:00, 17:00
         → run logged
9:42:00  start the-pet-pantry
         → last30 fetch (4 trends)
         → telegram down (network blip)
         → fall through to agent-mode prompt, but cron is non-interactive,
           so loop autoassigns autopilot for the day
         → branded-carousel produces 6 slides
         → postiz drafts 1 post (day 2 of 7)
         → run logged with checkin_status="telegram_failed"
9:50:00  cron complete
```

### Doctor at 9am for status

```bash
./doctor.sh
```

Expected per-brand block:

```
[PASS] kit installed at /Users/.../slideshow-kit
[PASS] gpt-image-2 API key present
[PASS] postiz CLI v2.0.13
[WARN] last30 skill not found in Codex (PASS in Claude Code)
[PASS] brand: acme (mode=draft, runs=4, formats=branded, postiz=2 integrations)
[PASS] brand: widget-co (mode=autopilot, runs=12, formats=branded+social-native, postiz=4 integrations)
[PASS] brand: the-pet-pantry (mode=draft, runs=2, formats=branded, postiz=2 integrations)
```

If widget-co had been autopilot at runs_history=4, you'd see:

```
[WARN] widget-co is in autopilot mode with only 4 runs of history (required: 7).
       See references/live-spend-gating.md.
```

## What the operator does each morning

- Reviews postiz UI for the 3 brands' drafts (acme + the-pet-pantry).
- Approves or edits drafts; postiz publishes them.
- Watches widget-co's autopilot posts go out at scheduled times.
- Hits Telegram replies if a hot take is needed.

The whole morning routine is < 15 minutes for 3 brands. The kit handles the production work; the operator owns taste.

## Failure mode walkthrough

### Postiz outage at 9am

- All 3 brands' loops fail at the publish step (exit 21).
- Each loop sends a Telegram alert ("[acme] postiz failed: see ...").
- Scripts and images are saved locally to `<brands_root>/<slug>/runs/<today>/`.
- Operator manually publishes from the saved files once postiz recovers.

### last30 outage at 9am

- All 3 brands log `[INFO] no trends today` and exit 0.
- runs_history still increments: the day "counted" even with no trends.
- No carousels, no postiz calls, no Telegram alerts (no actionable failure).
- Tomorrow the loop tries again with fresh trends.

### One brand's telegram_chat_id is wrong

- Just that brand's check-in falls through to autopilot (channel="agent" mode but cron is non-interactive → autopilot).
- Other brands unaffected.
- Operator catches it via `doctor.sh` showing `checkin_status="telegram_failed"` in latest run-summary.

## Scaling beyond 3 brands

10+ brands? Run them in parallel with GNU parallel or split crons:

```cron
0 9 * * * cd ~/Documents/GitHub/slideshow-kit && SLIDESHOW_BRAND=acme ./scripts/run-daily-loop.sh
0 9 * * * cd ~/Documents/GitHub/slideshow-kit && SLIDESHOW_BRAND=widget-co ./scripts/run-daily-loop.sh
# ...
```

Each brand has independent rate-limit envelopes (gpt-image-2 + postiz), so parallel runs are safe up to your API quotas. Watch for postiz rate limits if you exceed ~20 concurrent brands.
