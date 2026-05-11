# Onboard Brand Workflow

Two-mode workflow that produces three brand DNA files at `<brands_root>/<slug>/`:
- `brand-voice.md`
- `brand-perspective.md`
- `visual-system.md`

Plus one or more reusable carousel styles at `<brands_root>/<slug>/styles/<style-name>/`
and, when social-native output is enabled, a character file at
`<brands_root>/<slug>/characters/character-default.md`.

## When to read this

The agent reads this workflow when the user asks to:
- onboard a new brand
- set up a new brand
- run brand voice extraction
- migrate a brand into slideshow-kit

## Pre-flight

1. Ask: "What's the brand slug? (lowercase, alnum + hyphens, used in paths)"
2. Ask: "Paste mode (you give me 5+ best socials and I extract DNA) or interview mode (I ask 12 questions)?"
3. Run `./scripts/init_brand.sh <slug>` to scaffold the workspace from templates.
4. If paste mode and user has fewer than 5 samples: switch to interview mode and tell the user why.

## Path A: Paste mode (default)

### A.1 Voice extraction

1. Read `references/voice-extraction-rubric.md` in full.
2. Ask: "Paste 5-10 of your best posts. One per code block, separated by `---`. Mix LinkedIn, X, threads, carousels - whatever you ship."
3. Once samples are pasted:
   - Walk the rubric in order (hook style → structural arc → signature phrases → length → anti-patterns → dialog patterns)
   - Extract pillar candidates (cluster by topic)
   - Extract ICP candidate (read the addresses + pain points)
4. Draft `brand-voice.md` by overwriting the template at `<brands_root>/<slug>/brand-voice.md`. Preserve the YAML frontmatter (update `extracted-from: paste`, `extracted-on: <today>`, `sample-count: <N>`).
5. Show the draft to the user, section by section. For each:
   - "Here's what I extracted for `# Voice Principles`. Confirm, edit, or replace."
   - Apply the user's edits before moving to the next section.
6. The voice file is shipped only when the user has confirmed every section.

### A.2 Perspective draft (pillars + ICP only)

7. Draft `brand-perspective.md`:
   - `# ICP` - from inference, end with `<TODO: confirm>`
   - `# Pillars` - 3-5 clusters from samples
   - `# Hot Takes` - leave empty with `<TODO: extracted in next step>`
   - `# Things We Don't Talk About` - leave empty
   - `# Trend Filters` - leave empty
8. Show user. Ask them to confirm/edit ICP and pillars. Move to A.3.

### A.3 Perspective extractor (hot takes sub-flow)

This sub-flow is what makes the kit different. Hot takes are the lens the daily-loop uses to translate trends, and they're the hardest piece to articulate without prompting.

9. Tell the user: "Now I'll surface 3-5 trend examples and ask your take on each. Your reactions become the brand's hot takes."
10. Generate or recall 3-5 *plausible* trend snippets relevant to the brand's pillars. Each snippet is one line + a default industry framing. Examples:

    - Pillar "AI for agencies":
      "Trend: agencies are layoffs-then-ai. Industry framing: 'AI replaced our 20-person team.'"
    - Pillar "founder content":
      "Trend: AI thumbnail tests. Industry framing: 'Run 8 thumbnails through MrBeast's tool.'"
    - Pillar "operator systems":
      "Trend: 'vibe coding' replacing engineers. Industry framing: 'Designers ship features now.'"

11. For each snippet, ask: "What's your take on this? What does the industry get wrong?"
12. After all 3-5 reactions are captured, paraphrase each into the format: "Most people think X. We think Y because Z."
13. Show the user the formatted hot takes. Confirm/edit each.
14. Write to `# Hot Takes` in `brand-perspective.md`.
15. Ask: "What topics do you avoid? List 3-5 - these become trend filters." Write to `# Things We Don't Talk About` and the negative side of `# Trend Filters`.
16. Ask: "When a trend comes in, what makes you react vs skip?" Write to `# Trend Filters`.

### A.4 Visual system

17. Ask: "Pick one:
    a) Paste a hex palette (background, primary accent, secondary accent, neutral)
    b) Pick a vibe and I'll suggest a palette: minimal-dark / editorial-light / candid-warm / bold-saturated
    c) Skip - I'll use defaults from `references/brand-templates/visual-system.md`"
18. Ask typography: massive bold / editorial serif / minimal sans / candid handwritten?
19. Ask layout: corporate / editorial / candid iPhone / branded SaaS?
20. Ask three words for the vibe.
21. Write to `<brands_root>/<slug>/visual-system.md`. Show. Confirm.

### A.5 Reusable styles

This is an operator conversation, not a CLI handoff. Never ask the user to run
`add_style.sh` themselves. The agent may use `scripts/add_style.sh` internally,
but the user-facing flow is natural language.

22. Tell the user:

    "Now let's define the reusable carousel styles for this brand. These are
    the visual recipes the kit can reuse every day. You can describe a style in
    words, give me screenshots/images/links as references, or do both."

23. Ask: "Which style lanes do you want to create now?
    a) Branded - brand palette, typography, designed carousel system
    b) Social-native - candid phone-style visuals with a recurring person
    c) Thread/native text - clean native text or screenshot-like slides
    d) More than one"

24. For each selected lane, ask for a plain-English description:

    - Branded example: "dark editorial, bold white type, rose accent, no photos"
    - Social-native example: "candid iPhone shots of me working, short captions"
    - Thread/native example: "clean LinkedIn-native text slides, almost like screenshots"

25. Ask: "Do you have visual examples for this style? You can provide 1-5
    screenshots, PNGs, links, or say `no examples`."

26. Convert the answer into a snake_case style name. Examples:

    - `branded_editorial`
    - `social_native`
    - `thread_native`
    - `iphone_candid_founder`

27. Create the style directory under `<brands_root>/<slug>/styles/<style-name>/`.
    Use `scripts/add_style.sh` internally when convenient:

    ```bash
    ./scripts/add_style.sh --brand <slug> --style <style-name> \
      --description "<operator description>" \
      --refs "<comma-separated local ref paths>"
    ```

    If the user provided links instead of local files, first fetch or otherwise
    save the useful visual references into the style's `refs/` directory. If
    references are not available, continue from the description alone and call
    out that the first proof render should be reviewed more carefully.

28. Replace the scaffolded `DESIGN.md` with a complete style definition:

    - YAML frontmatter with `name`, `extends`, palette, typography, layout,
      `image_treatment`, and `ui_chrome`.
    - Markdown body with purpose, mood, do rules, don't rules, and when to swap
      to another style.
    - Use `extends: brand` unless the user explicitly wants to ignore the brand
      visual layer.

29. Show the style summary to the user and ask them to confirm or edit. Do not
    mark onboarding complete until each selected style is confirmed.

30. Ask: "Which style should be the default, and which styles should run on a
    normal day?" Then update `<brands_root>/<slug>/config.json`:

    ```json
    {
      "default_style": "<style-name>",
      "styles_per_day": ["<style-name>", "..."]
    }
    ```

31. If the user chooses a social-native or candid-person style, continue to the
    character steps below. If the user chooses only designed/text styles, skip
    character creation unless they explicitly want a recurring person.

### A.6 Character bible (optional, for social-native styles)

Skip this step entirely if the brand only uses designed or text-native styles
without recurring characters.

If the brand will use a social-native or candid-person style (iPhone-real
candid posts with the same person across slides), build a character bible.

1. Create the directory: `<brands_root>/<slug>/characters/`
2. Copy the template:

   ```bash
   cp examples/character-bible-example.md <brands_root>/<slug>/characters/default.md
   ```

3. Fill in the required sections using `examples/character-bible-example.md`
   as the schema. Required sections: `# Identity`, `# Locked physical traits`,
   `# Wardrobe baseline`, `# Story world`, `# Continuity rules`. Optional:
   `# Anti-patterns specific to this character`, `# Reference images`.

4. Add ONE neutral reference photo to `<brands_root>/<slug>/characters/`. PNG, 1024 px or larger on the short edge, no styling, in the brand's typical environment family. Register the filename under `# Reference images` in the character file.

5. Recommended: run the face-continuity diagnostic to pick the right `--mode` for this character:

   ```bash
   python evals/diagnostics/face_continuity_2026_05_04.py \
     --brand <slug> \
     --script <a-5-slide-test-script.md> \
     --output-root brands/<slug>/runs/$(date +%Y-%m-%d)-diag

   python evals/diagnostics/face_score.py \
     --dir brands/<slug>/runs/$(date +%Y-%m-%d)-diag/control \
     --dir brands/<slug>/runs/$(date +%Y-%m-%d)-diag/batch \
     --dir brands/<slug>/runs/$(date +%Y-%m-%d)-diag/anchor \
     --output brands/<slug>/runs/$(date +%Y-%m-%d)-diag/face-scores.json
   ```

   Cost: ~$1.20 OpenAI gpt-image-2 + ~$0.03 gpt-4o-mini scoring.

6. Inspect the 15 PNGs visually + read the score table. The kit default is `anchor-chain`; if a different mode wins for this character, set it in `<brands_root>/<slug>/config.json`:

   ```json
   {
     "snc_mode": "per-slide"
   }
   ```

   Resolution priority: explicit `--mode` flag > `snc_mode` in config.json > kit default `anchor-chain`.

### A.7 Default character (for social-native styles)

32. Tell the user: "This social-native style needs a recurring character. I can draft one from your ICP, or you can describe the person."
33. Read `# ICP` from `brand-perspective.md`.
34. Draft a character file at `<brands_root>/<slug>/characters/character-default.md` per the available character schema.
35. Show the draft. Ask the user to confirm or replace. Specifically check:
    - Age band
    - Gender presentation (offer to flip)
    - Facial hair / haircut / build
    - Wardrobe baseline
    - Environment family
    - Whether the user has neutral reference photos to add
36. Apply edits, save. If the user provides reference photos, copy them into
    `<brands_root>/<slug>/characters/` and the matching style `refs/`
    directory, then register them in the character file.

### A.8 Validation

37. Run `python3 scripts/validate_brand.py --brand-dir <brands_root>/<slug>`. If FAIL, surface errors and walk the user through fixing each.
38. Run `./doctor.sh`. Confirm `[PASS] brand[<slug>]: all DNA files present` shows up.
39. Run `./scripts/list_styles.sh <slug>` and confirm the intended default and
    daily styles are listed.
40. Tell user: "Onboarding done. I created your reusable style(s), set the
    default style, and the kit is ready for a dry proof render."

## Path B: Interview mode

12 questions across 3 sections. Each section drafts its file before moving on.

### B.1 Voice (4 questions)

1. "Describe how you talk to your audience in one sentence." → write to `# Voice Principles` (paraphrase as 3 imperatives if user gives one sentence).
2. "Paste a recent post you liked." (1 sample minimum) → use the post to fill `# Signature Patterns` and `# Structure`.
3. "What words / phrases do you NEVER use?" → `# What NOT to Do`.
4. "What's your typical post length per platform? Give a rough character count." → `# Length / Format`.

Draft `brand-voice.md`. Show. Confirm.

### B.2 Perspective (4 questions)

5. "Who specifically are you talking to?" → `# ICP`.
6. "What 3-5 things do you stand for?" → `# Pillars`.
7. "What's a hot take you have that the industry disagrees with?" → first `# Hot Takes` entry.
   Then run the perspective extractor sub-flow (A.3 steps 9-14) to surface 2-4 more hot takes.
8. "What topics do you avoid?" → `# Things We Don't Talk About` and the skip side of `# Trend Filters`. Then ask the react-side: "What makes you react to a trend?" → `# Trend Filters`.

Draft `brand-perspective.md`. Show. Confirm.

### B.3 Visual (4 questions)

9. "Pick 4 colors (hex), or pick a vibe and I'll generate them: minimal-dark / editorial-light / candid-warm / bold-saturated."
10. "Headline style: massive bold / editorial serif / minimal sans / candid handwritten?"
11. "Layout: corporate / editorial / candid iPhone / branded SaaS?"
12. "Three words for the vibe." → `# Vibe Rules` `Tone:` line.

Draft `visual-system.md`. Show. Confirm.

Then run A.5 (reusable styles), A.6-A.7 only if a social-native/candid-person
style is selected, and A.8 (validation).

## Idempotency

If `<brands_root>/<slug>/` already has DNA files, ask the user: "This brand exists. Re-onboard (overwrite) or update specific files? Run `init_brand.sh <slug> --force` first if re-onboarding."

## Output contract

After this workflow completes:
- `<brands_root>/<slug>/brand-voice.md` - valid against `scripts/validate_brand.py`
- `<brands_root>/<slug>/brand-perspective.md` - valid
- `<brands_root>/<slug>/visual-system.md` - valid
- `<brands_root>/<slug>/styles/<style-name>/DESIGN.md` - present for each selected style
- `<brands_root>/<slug>/styles/<style-name>/refs/*` - present when the user supplied visual examples
- `<brands_root>/<slug>/characters/character-default.md` - present when a social-native/candid-person style is selected
- `<brands_root>/<slug>/config.json` - includes `default_style` and `styles_per_day`
- `./doctor.sh` reports the brand as healthy

## Hard rules

- **No fabrication.** Never invent a hot take, a pillar, or a personal detail. Use `<TODO: confirm>` whenever uncertain.
- **Show, don't ship silently.** Every drafted section gets the user's eyes before moving to the next file.
- **Save-first.** If the user pauses mid-onboarding, every confirmed section is already on disk. They can resume.
- **Brand voice precedence.** When the brand voice contradicts a generic best-practice, the brand voice wins.
