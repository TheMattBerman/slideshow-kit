# Example: Voice Extraction Before/After

How the kit's voice-extraction-rubric (Plan 2) turns 7 raw posts into a structured `brand-voice.md`. Use this as a sanity check before onboarding a new brand. If your output looks like the "Before" column for the wrong brand, the rubric isn't being followed.

## Source: 7 paste-mode samples (anonymized)

```
1. "i used to think landing pages were a content problem. they're a copy problem.
    here's what changed when i fixed mine: → bounce rate down 41% → conv up 2.3x → demos doubled."
2. "stopped writing 'engaging content.' started writing emails my friends would forward.
    same brand, 3x reply rate."
3. "→ stop A/B testing buttons → start A/B testing PROOF → that's where the lift is."
4. "the founder who outwrites their team has more leverage than the founder who out-engineers theirs.
    in 2026 this isn't optional."
5. "ran a $0 launch this week. 8,400 signups. here's the playbook:
    → cold email 200 ICP-aligned operators
    → ask for feedback, not signups
    → publish the responses verbatim
    → let the audience opt in"
6. "i can't believe i'm saying this but: spreadsheet > deck for narrative selling.
    decks lie. spreadsheets compress."
7. "if you can't summarize your offer in 11 words, you don't have an offer.
    you have a feature list."
```

## Before: naive extraction (bad)

If you skip the rubric and just ask the agent for a voice doc, you tend to get:

```markdown
# Voice Principles
- Be authentic and engaging
- Use concrete examples
- Speak directly to your audience
- Vary sentence length

# Structure
Hook + body + CTA

# Length / Format
Short and punchy
```

This is generic. It would describe 90% of B2B founder accounts. It cannot be operationalized.

## After: rubric-driven extraction (good)

Following `references/voice-extraction-rubric.md` (Plan 2 deliverable), the agent extracts:

```markdown
---
brand: example
extracted-from: paste
extracted-on: 2026-05-04
sample-count: 7
---

# Voice Principles
- Lowercase. No capitalization except for ALL CAPS emphasis on 1-2 words per post.
- Open with confession or contrarian frame ("i used to...", "i can't believe...").
- Arrow bullets ( → ) inside posts, never bullets with dashes.
- Specific numbers beat ranges (8,400 not "thousands"; 2.3x not "more").
- End with a one-sentence universal truth or CTA.

# Structure
HOOK (confession/contrarian)
→ SETUP (one line of context)
→ 3-5 ARROW BULLETS (specific concrete moves)
→ KICKER (the universal-truth close)

Most posts are 3-7 lines, including the bullets.

# Signature Patterns
- Confession openers: "i used to think X.", "stopped Xing.", "i can't believe i'm saying this but:"
- Contrarian openers: "the founder who X has more leverage than..."
- Concrete proof bursts: "bounce 41% down", "8,400 signups", "$0 launch"
- Comparison kickers: "decks lie. spreadsheets compress.", "you have a feature list."
- ALL CAPS emphasis on PROOF, EMPHASIS, single nouns. Never on adjectives.

# What NOT to Do
- Title Case headlines.
- LinkedIn-bro hooks ("Most people don't realize...", "Here's what NOBODY is talking about").
- Em dashes (this brand uses commas + line breaks for beat changes).
- Vague ranges ("a lot", "many", "some").
- Multi-paragraph essays. Every sample is < 8 lines.
- "Engagement bait" CTAs ("comment below", "what do you think?").

# Length / Format
- LinkedIn: 400-700 chars body
- X: 280 chars max, splits to thread when over
- IG/Threads: 700-1200 chars body
- Carousels: 6 slides, slide 1 = HOOK, slide 6 = CTA
```

## Before/after diff: what the rubric forces you to surface

| Before (naive) | After (rubric) |
|---|---|
| "Be authentic" | "Open with confession or contrarian frame": operationalized |
| "Concrete examples" | "8,400 signups, 2.3x, $0 launch": proves voice with samples |
| "Vary sentence length" | "3-7 lines including bullets": measurable |
| (no anti-patterns) | 6 explicit anti-patterns this brand never does |
| (no signature phrases) | 4 specific opener patterns + 2 kicker patterns |

## How to validate

After running the rubric:

1. Pick a fresh sample NOT in the 7 used for extraction.
2. Score it against the principles. 4+/5 of the principles should match. If not, the extraction missed something.
3. Generate a fake post using only the rubric output (no examples). Check if the brand operator says "yes, that's me" or "no, that's not me." If the latter, iterate on the rubric.

## When to re-run extraction

- Voice noticeably evolves (e.g. shifts from formal to lowercase, or vice versa).
- The kit's output starts feeling off. Usually a sign the brand has drifted but the doc hasn't.
- New format added (e.g. brand starts shipping carousels and the existing voice is post-only).

The kit's v1.1 voice-drift detector will flag drift automatically. For v1, treat re-extraction as a quarterly chore.
