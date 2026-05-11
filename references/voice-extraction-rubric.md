# Voice Extraction Rubric

What the agent looks for when analyzing 5-10 social samples to extract a brand's voice. Used by `workflows/onboard-brand.md` paste mode.

## Goal

Produce three artifacts from samples alone:
1. A `brand-voice.md` matching the schema in `references/brand-templates/brand-voice.md`
2. A first-draft `brand-perspective.md` with at least pillars and ICP (hot takes are extracted in a follow-up sub-flow)
3. A first-draft `visual-system.md` if the samples include images, otherwise prompted from user

## Sample sufficiency

- **5+ samples required** for paste mode. Below that, switch to interview mode.
- Mix is better than monoculture: 2 hooks-only posts + 2 long-form posts + 1 thread > 5 of the same format.
- If samples are all from the same week, ask the user for one older sample so you can detect voice drift.

## What to extract

Walk the samples in order. For each sample, capture:

### 1. Hook style
Patterns to look for:
- Specific scene ("I watched a founder stare at a tripod for 20 minutes.")
- Number lead ("30 conversations this year.")
- Direct claim ("Most agencies are running last-cycle plays.")
- Question ("Why does AI feel like a chore?")
- List tease ("3 things I changed this quarter:")
- Quoted dialogue ("'I know I should be posting video.'")

Tally which type recurs most. That's the brand's default hook.

### 2. Structural arc

Read each sample as a sequence of beats. Common arcs:
- HOOK → SCENE → INSIGHT → OPEN (Matt's pattern)
- HOOK → 3-LIST → CLOSE
- HOOK → CONTRARIAN_TAKE → EVIDENCE → INVITATION
- HOOK → STORY → MECHANISM → OUTCOME

Identify the arc that fires in 3+ of the samples.

### 3. Signature phrases

Hunt for:
- Reveal phrases ("Here's the thing —", "And that's when I realized")
- Closing patterns (question, invitation, soft CTA, hard CTA, no CTA)
- Repeated metaphors / objects ("unopened boxes", "ring light still in plastic")
- Pop-culture touchstones (specific people, brands, shows referenced more than once)
- Numbers that recur ("30 times this year", "20-30 million views")
- Vulnerable admissions ("I haven't solved this yet", "I'm still figuring this out")

Quote 2-3 verbatim from the samples in `# Signature Patterns`.

### 4. Length

Capture per platform (if mix is in samples):
- LinkedIn: median + range of character count
- X: median + range
- IG caption: median + range
- Carousel slide copy: max words per slide observed

### 5. Anti-patterns the brand avoids

Scan for what's NOT there:
- No emojis? Note it.
- No hashtags? Note it.
- No "I" statements? (rare — usually means corporate voice)
- No second-person "you"? (rare — usually means observer voice)
- No exclamation points? Note it.
- No direct CTAs? Note it.

These become `# What NOT to Do` entries.

### 6. Dialog patterns

If multiple samples contain dialogue:
- Format: short two-line exchanges? long monologues? quoted with names? quoted anonymously?
- Real names or "Founder:" / "Me:"?
- Present tense or past tense?

### 7. Pillar inference (for brand-perspective.md draft)

Cluster the samples by topic. 3-5 clusters = the brand's pillars. Examples for Matt: "AI for agencies", "founder content", "voice/personality", "operator-grade systems". Each pillar is one line.

### 8. ICP inference

Look at the samples for:
- "If you're a [X]" — direct addresses to a role
- "Most [X] are doing Y" — third-person addresses
- Pain points named (operational, emotional, identity-level)

Draft a one-paragraph ICP. Always end with `<TODO: confirm with user>` so the user knows it's inferred.

## What NOT to extract

These come from the user, not the samples:
- Hot takes (use the perspective extractor sub-flow)
- Things the brand avoids talking about
- Trend filters
- Visual palette / typography (unless samples include consistent visuals)

## Confidence calibration

For each extracted item, mark:
- HIGH (recurs in 4+ samples) — write to file directly
- MEDIUM (recurs in 2-3) — write to file but flag in `<TODO: confirm with user>`
- LOW (single occurrence) — don't write, but mention in the user check-in: "I noticed X once. Is that part of the voice or a one-off?"

## Output discipline

Never invent. If a `brand-voice.md` schema field can't be filled from samples, use:
- `<TODO: confirm in interview>` for things the user must answer
- Empty bullets (just `-`) for things genuinely absent

The agent's draft is a *first pass*, not a final artifact. The user must confirm or edit each section before the file is considered shipped.
