# Slideshow Kit

**A daily brand-DNA-driven carousel engine that turns trend signal, point of view, and reusable visual styles into publishable social slideshow packs.**

Built for Claude Code, Codex, OpenClaw, Hermes, and any agent workflow that can read skills.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Agent Ready](https://img.shields.io/badge/Agent-ready-6D28D9)](#skills)
[![Pipeline](https://img.shields.io/badge/Pipeline-DNA%20%E2%86%92%20Concept%20%E2%86%92%20Slides-F43F5E)](#the-pipeline)

---

**Brand DNA -> Trend Signal -> Concept Slate -> Script -> Scene Direction -> Styled Carousel -> Publish Pack**

Slideshow Kit automates the social carousel workflow most teams still run by hand:

- **Onboard the brand** - Extract voice, beliefs, visual system, and reusable style rules from real samples
- **Find the angle** - Turn trend input and operator hot takes into ranked carousel concepts
- **Write the script** - Draft a format-compliant carousel with hook patterns, close actions, and save-worthy density
- **Direct the visuals** - Generate per-slide scene briefs before rendering so the image matches the argument
- **Render the carousel** - Produce style-driven PNG slides through `gpt-image-2` or Codex-native generation
- **QA the output** - Lint voice, format, word caps, save-worthiness, and render completion
- **Package for publishing** - Create local run artifacts, Postiz drafts/schedules, Telegram alerts, and run logs

The result: a repeatable carousel production loop that sounds like the brand, looks like the brand, and leaves behind the artifacts an operator needs to review, rerun, or publish.

---

## Why This Exists

Most social teams do not have an ideas problem.

They have a **repeatability and taste problem**.

One good carousel is easy. A consistent carousel machine is hard. You need a real point of view, a voice that does not collapse into generic AI copy, visual systems that survive across formats, and enough QA that the output is worth posting without a 45-minute rescue pass.

Most AI carousel tools skip the hard part. They give you templates, generic hooks, and a deck that looks like an ad.

Slideshow Kit starts from brand DNA. It reads how the brand talks, what it believes, what it refuses to say, how its visual system works, and which social-native formats fit the channel. Then it turns trend signal into a structured carousel run: concepts, script, scene direction, slides, prompts, logs, and publish payloads.

Not a prompt dump.
Not a Canva template pack.
Not a generic auto-poster.

**A carousel operating system for people who want a daily social machine without losing the voice.**

---

## The 10-Second Mental Model

| Layer | Question |
|---|---|
| **Brand DNA** | Who does this need to sound like and look like? |
| **Trend Signal** | What is worth reacting to today? |
| **Concept Slate** | What are the strongest angles we could ship? |
| **Script** | How does the argument unfold slide by slide? |
| **Scene Direction** | What should each slide actually show? |
| **Styled Render** | Which reusable visual recipe should package this idea? |
| **Publish Pack** | What does the operator need to review, schedule, or rerun? |

The loop is the product.

---

## What It Does

```text
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Brand DNA   │ → │   Concept    │ → │    Script    │ → │    Scene     │
│ Voice + POV  │   │    Slate     │   │ Format-safe  │   │  Direction   │
└──────────────┘   └──────────────┘   └──────────────┘   └──────┬───────┘
                                                                 │
       ┌─────────────────────────────────────────────────────────┘
       ↓
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│    Render    │ → │      QA      │ → │   Publish    │
│ Styled PNGs  │   │ Logs + Lints │   │ Postiz/Files │
└──────────────┘   └──────────────┘   └──────────────┘
```

Every run is artifact-backed. The agent is not just producing slides; it is producing a traceable packet:

- `concepts.md` - 5-10 ranked concepts with hook variants and visual hooks
- `concept-pick.md` - the selected concept and hook
- `script.md` - frontmatter-compliant carousel script
- `scene-direction.md` - per-slide visual briefs
- `concept-meta.json` - structured concept and visual metadata
- `prompts.json` - exact image prompts
- `output-log.json` - render status, timing, model/provider, and per-slide results
- `post-NN.json` - publish payloads for Postiz or manual scheduling

That is what makes the workflow recoverable. If a render partially fails, you can see which slide failed. If a concept was weak, you can inspect the score and hook pattern. If a style misses, you can adjust the style system instead of rewriting the whole kit.

---

## What Makes This Different

1. **Brand DNA before generation** - Voice, perspective, visual system, and style rules are first-class inputs, not after-the-fact instructions.
2. **Concepts before scripts** - The kit ranks angles before it writes slides, so you choose the move before polishing the execution.
3. **Formats are explicit** - Narrative, diagnostic, receipt/context, process reveal, anatomy breakdown, before/after, and counter-narrative formats have real slot rules.
4. **Visuals are directed before render** - Scene direction happens at script time, so the image is part of the story, not a decorative afterthought.
5. **Styles are reusable assets** - Each brand can keep named styles under `styles/<name>/`, with `DESIGN.md`, refs, and optional word-cap overrides.
6. **QA is built into the path** - Voice lint, format lint, save filter, prompt logs, and partial-render accounting all happen before the operator ships.
7. **Agent-native, not platform-locked** - Works through Claude Code, Codex, OpenClaw, Hermes, or a plain local checkout.

---

## The Pipeline

### 1. Onboard A Brand

Every brand gets a local workspace with three DNA files:

```text
brands/<slug>/
├── brand-voice.md
├── brand-perspective.md
├── visual-system.md
├── config.json
└── styles/
    └── <style-name>/
        ├── DESIGN.md
        ├── style.yaml
        └── refs/
```

Use paste mode when you have 5-10 strong posts. Use interview mode when the brand does not have enough samples yet.

### 2. Generate Concepts

The `concept-generator` skill turns trend input and brand corpus into ranked concepts. Each concept includes:

- format
- close action
- arc
- why it works
- personal-fact risk
- hook variants
- visual hook
- concept score

Interactive mode can pause for operator specifics. Autopilot mode avoids personal-fact concepts and picks a safer concept automatically.

### 3. Draft The Script

The selected concept becomes `script.md`, with YAML frontmatter and section headings that match one of the supported carousel formats. The lint chain checks:

- brand voice violations
- em dashes and AI-tell phrases
- slot count and word count
- close-action vocabulary
- save-worthiness markers like numbers, dates, named frameworks, quotes, or tactical asides

### 4. Direct The Scenes

The visual director writes `scene-direction.md`, one concrete visual brief per slide. Character-driven styles get content-matched variety instead of the same desk, same crop, same expression across every slide.

### 5. Render The Carousel

The `styled-carousel` skill merges:

```text
kit defaults <- brand visual-system.md <- style DESIGN.md/style.yaml
```

Then it renders each slide in the requested sizes. In Codex Desktop, `--provider auto` prepares Codex-native generation requests. In shell/API mode, it can call the OpenAI image API.

### 6. Package And Publish

The daily loop can create publish payloads and route them through Postiz. Telegram check-ins and alerts are optional and isolated, so a Telegram issue does not block publishing and a Postiz issue does not destroy the local run.

---

## Skills

| Skill | What It Does |
|---|---|
| `slideshow-kit` | Top-level router for brand onboarding, carousel generation, daily loop, brand management, and style work |
| `concept-generator` | Generates concepts, selects one, drafts the carousel script, and writes concept metadata |
| `styled-carousel` | Renders a script into style-driven carousel PNGs with prompts and output logs |

Supporting workflows:

| Workflow | What It Does |
|---|---|
| `workflows/onboard-brand.md` | Extract brand voice, perspective, visual system, and default style |
| `workflows/daily-loop.md` | Trends -> check-in -> concepts -> script -> render -> publish -> log |
| `workflows/checkin.md` | Operator hot-take collection through Telegram or in-session review |

---

## Supported Carousel Formats

| Format | Use When |
|---|---|
| `narrative` | Story-driven lessons, case studies, and founder POV |
| `numbered_diagnostic` | "The 4 tells", "5 reasons your X is broken", diagnostic posts |
| `receipt_context` | Quote, screenshot, or claim followed by interpretation |
| `process_reveal` | "How I did X in N minutes" or workflow breakdowns |
| `anatomy_breakdown` | Teardowns, examples, and what-to-notice posts |
| `before_after` | Transformation, contrast, and old-way/new-way posts |
| `counter_narrative` | Contrarian takes on category orthodoxy |

See `references/formats/README.md` for slot templates and aliases.

---

## Quick Start

### 1. Clone And Install

```bash
git clone https://github.com/TheMattBerman/slideshow-kit.git
cd slideshow-kit
./install.sh
```

`install.sh` detects installed agents and installs the kit where it can:

- `~/.claude/skills/`
- `~/.codex/skills/`
- `~/.clawd/skills/`
- Hermes plugin paths when configured

### 2. Check Your Environment

```bash
./doctor.sh
```

The doctor checks agent installs, image-generation keys, Postiz auth, optional Telegram setup, and brand DNA files.

### 3. Create A Brand

```bash
./scripts/init_brand.sh matt
```

Then fill the core DNA files:

```bash
$EDITOR ./brands/matt/brand-voice.md
$EDITOR ./brands/matt/brand-perspective.md
$EDITOR ./brands/matt/visual-system.md
```

Or let the agent onboard the brand from samples:

```text
Onboard a new brand called `matt`. I'll paste 5-10 of my best social posts.
```

### 4. Render A Dry Run

```bash
python skills/styled-carousel/scripts/generate_styled_carousel.py \
  --brand matt \
  --script examples/test-script.md \
  --output ./brands/matt/runs/$(date +%F)/ \
  --dry-run
```

Dry run writes prompts and logs without spending image-generation credits.

### 5. Run A Styled Carousel

```bash
python skills/styled-carousel/scripts/generate_styled_carousel.py \
  --brand matt \
  --style social_native \
  --script examples/test-snc-script.md \
  --output ./brands/matt/runs/$(date +%F)/
```

---

## Daily Loop

Once a brand is onboarded:

```bash
export SLIDESHOW_BRAND=matt
```

Then ask your agent:

```text
Run today's slideshow loop for matt.
```

The loop:

1. Loads brand DNA
2. Applies the live-spend gate
3. Invokes trend research
4. Collects or skips operator check-in
5. Generates concepts
6. Picks and drafts the script
7. Writes scene direction
8. Renders the configured styles
9. Builds Postiz payloads
10. Logs the run

Autopilot is intentionally gated. A brand needs 7+ draft/history runs before autopilot mode is allowed to spend or schedule without daily review. See `references/live-spend-gating.md`.

---

## Brand And Style Management

```bash
./scripts/init_brand.sh client-acme
./scripts/list_brands.sh
./scripts/switch_brand.sh client-acme
./scripts/list_styles.sh client-acme
```

Create a new reusable visual style:

```bash
./scripts/add_style.sh --brand client-acme --style founder-notes
```

Style state lives with the brand, not inside the kit. That keeps client-specific voice, references, and visual decisions out of the repo.

Custom brand roots are supported:

```bash
export SLIDESHOW_BRANDS_ROOT="$HOME/work/brands"
```

See `references/brand-management.md` and `references/style-system.md` for the full rules.

---

## Output

A typical run directory looks like:

```text
brands/matt/runs/2026-05-08/
├── trends.json
├── checkin-response.md
├── concepts.md
├── concept-pick.md
├── script.md
├── scene-direction.md
├── concept-meta.json
├── prompts.json
├── output-log.json
├── social_native-slide-01-1024x1024.png
├── social_native-slide-02-1024x1024.png
├── ...
├── post-01.json
└── run-summary.json
```

The important part: this is not a black box. Every decision and every render can be inspected.

---

## API Keys And What's Free

| Level | APIs | What Works |
|---|---|---|
| **Dry run** | None | Brand setup, scripts, prompts, linting, logs |
| **Codex-native generation** | Codex Desktop image generation | Native request packets and agent-mediated image creation |
| **OpenAI API rendering** | `OPENAI_API_KEY` | Direct `gpt-image-2` render path, visual director, face/continuity checks where enabled |
| **Publishing** | Postiz CLI auth | Draft or scheduled carousel posts |
| **Check-ins / alerts** | Telegram bot token | Optional daily review and failure alerts |

Start with dry runs. Add live rendering only after the script and style are working.

---

## Non-Negotiables

1. **Brand voice beats generic polish.** If it does not sound like the brand, it fails.
2. **One idea per carousel.** A crowded carousel is a weak argument with slide numbers.
3. **The hook must earn the swipe.** Slide 1 is not a title slide.
4. **Format rules are real.** Slot count, word count, close action, and save-worthiness are gates.
5. **Visuals must serve the argument.** Pretty-but-random scenes are not good output.
6. **Draft mode comes before autopilot.** Live scheduling is earned through run history.
7. **The run packet is the deliverable.** PNGs matter, but prompts, logs, script, and metadata make the workflow reusable.

---

## Project Structure

```text
slideshow-kit/
├── README.md
├── CHANGELOG.md
├── SKILL.md
├── SUITE.md
├── SPEC.md
├── AGENTS.md
├── CLAUDE.md
├── install.sh
├── uninstall.sh
├── doctor.sh
├── skills/
│   ├── concept-generator/
│   └── styled-carousel/
├── workflows/
│   ├── onboard-brand.md
│   ├── daily-loop.md
│   └── checkin.md
├── scripts/
│   ├── init_brand.sh
│   ├── add_style.sh
│   ├── list_brands.sh
│   ├── list_styles.sh
│   ├── publish_postiz.sh
│   └── send_telegram.sh
├── lib/
├── references/
│   ├── formats/
│   ├── styles/
│   ├── concept-patterns/
│   └── brand-templates/
├── examples/
├── evals/
└── tests/
```

---

## More Operator Kits

Slideshow Kit sits in the same family as the rest of the agent kit stack:

- [100k Posts Kit](https://github.com/TheMattBerman/openclaw-100k-posts-kit) - performance signal into weekly content ideas
- [Creator Breakout Kit](https://github.com/TheMattBerman/creator-breakout-kit) - creator concepts before sourcing or production
- [Landing Page Factory](https://github.com/TheMattBerman/landing-page-factory) - URL to deployable landing page
- [Brand Shoot Kit](https://github.com/TheMattBerman/brand-shoot-kit) - ecommerce visual production loop
- [Outcome Kit](https://github.com/TheMattBerman/outcome-kit) - real winners, fake winners, leaks, and next moves

Slideshow Kit owns the carousel lane: brand-native, social-native, repeatable posts that can be generated, reviewed, and published every day.

---

## The Big Idea

The future of social content is not asking AI for posts.

It is a production loop:

```text
Signal -> point of view -> native format -> visual system -> QA -> publish -> memory
```

Slideshow Kit is that loop in repo form.

---

## License

MIT License. See `LICENSE`.

---

Built by [Matt Berman](https://twitter.com/themattberman).

- Twitter/X: [@themattberman](https://twitter.com/themattberman)
- Newsletter: [Big Players](https://bigplayers.co)
- Agency: [Emerald Digital](https://emerald.digital)

This is for operators who want a daily carousel system, not another folder of prompts.
