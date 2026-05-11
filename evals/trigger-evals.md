# Trigger Evals: slideshow-kit

When does the agent invoke the slideshow-kit skill correctly vs wrongly? Each row is a test prompt + expected behavior. Run these by pasting the prompt to your host agent (Claude Code, Codex, OpenClaw, Hermes) and checking the response.

## Format

| Prompt | Expected | Anti-expected |
|---|---|---|

## Should trigger slideshow-kit

| Prompt | Expected | Anti-expected |
|---|---|---|
| "run today's slideshow loop" | Invokes `workflows/daily-loop.md` against default brand | Asks for brand-management.md or generates one-off content |
| "run the daily loop for matt" | Resolves brand=matt, runs daily-loop | Picks default brand instead |
| "generate today's branded carousel for acme" | Invokes `skills/branded-carousel/` with brand=acme | Invokes social-native-carousel by mistake |
| "make a candid iPhone-real carousel for matt" | Invokes `skills/social-native-carousel/` with brand=matt | Picks branded-carousel by mistake |
| "set up a new brand: client-foo" | Invokes onboarding workflow (`workflows/onboard-brand.md` from Plan 2) | Edits an existing brand |
| "what's the daily-loop status for last week?" | Reads `<brands_root>/<slug>/runs/` and summarizes | Re-runs the loop |
| "switch default brand to client-acme" | Invokes `scripts/switch_brand.sh` | Edits config files manually |
| "show me my brands" | Invokes `scripts/list_brands.sh` | Lists files in repo |

## Should NOT trigger slideshow-kit

| Prompt | Expected | Anti-expected |
|---|---|---|
| "write me a single LinkedIn post" | Use the host's general-purpose post skill | Invokes branded-carousel for one slide |
| "what does brand X believe?" | Reads `brand-perspective.md` directly, no kit invocation needed | Runs daily loop |
| "make me a YouTube thumbnail" | Different skill, not slideshow-kit | Invokes branded-carousel anyway |
| "I want a video ad" | Different skill (ai-video-ad-orchestrator) | Invokes social-native-carousel |
| "edit my brand voice" | Direct edit of `brand-voice.md` | Re-runs onboarding |
| "what's trending in AI today?" | Invokes `last30` directly | Invokes daily-loop |

## Edge cases

| Prompt | Expected | Anti-expected |
|---|---|---|
| "run the loop" (no brand, no default) | Errors with: "no brand resolved, pass --brand or set a default" | Picks first brand alphabetically |
| "run loop for brand-with-typo" | Errors: "brand workspace not found" | Creates the brand silently |
| "run loop in autopilot for new brand (runs_history=0)" | Refuses with live-spend gate message | Runs anyway |
| "run loop, telegram is down" | Logs WARN, falls through to autopilot for that day, postiz still runs | Crashes with telegram error |
| "run loop, postiz is down" | Saves images locally, sends telegram alert (if avail), exits 21 | Silently succeeds with no posts |

## Test execution

Manual. After each Plan 3 ship and after any change to `workflows/daily-loop.md` or skill descriptions, paste each prompt above and verify behavior.

## Pass criteria

20+ of the rows match expected behavior. Document any miss with a quote of the actual response and a one-line analysis (was the description ambiguous? was a related skill better-described and stole the trigger?).
