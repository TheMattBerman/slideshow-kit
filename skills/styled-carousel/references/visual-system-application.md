# Visual System Application

How to translate a brand's `visual-system.md` into prompt instructions for gpt-image-2.

## What we extract

From `visual-system.md`:
- **Palette** → hex codes for background, primary accent, secondary accent, neutral
- **Typography** → headline weight + case, body weight + case, pull-quote treatment
- **Layout** → slide arc, negative space rule, icon style
- **Vibe Rules** → tone keyword, list of things to avoid

## Prompt template per slide role

Each generated prompt has SIX blocks. The order matters: gpt-image-2 weights early instructions more.

```
1. SLIDE TYPE  ("HOOK slide", "EXAMPLE slide", etc.)
2. CANVAS      ("Square 1024×1024" / "Portrait 1024×1536" / "Story 1024×1792")
3. BACKGROUND  ("Solid background, hex #<bg-hex>")
4. TYPOGRAPHY  (weight, case, hierarchy, exact text)
5. ACCENT      (where to use primary accent, where to use secondary)
6. ANTI-META   ("No 'Slide X of Y'. No watermark. No frame border. No URLs.")
```

## Example: HOOK slide

Brand visual system says:
- Background: `#0D1117`
- Primary accent: `#F43F5E` (pink)
- Headline: extra-bold, UPPERCASE
- Tone: minimal

Prompt:

```
HOOK slide. Square 1024×1024.
Solid background, hex #0D1117.
ONLY the headline "I WORK 24 HOURS A DAY": extra-bold, UPPERCASE, massive white typography filling 70% of width, centered.
KEY WORDS "24 HOURS" highlighted in #F43F5E.
NO subtitle. NO icons. NO frame border. NO meta text. Stark and minimal.
```

## Example: OUTCOME slide

Same brand. Secondary accent for outcomes is yellow `#FACC15`.

Prompt:

```
OUTCOME slide. Square 1024×1024.
Solid background, hex #0D1117.
Headline "I WAKE UP WITH LEVERAGE.": extra-bold, UPPERCASE, white. KEY WORD "LEVERAGE" highlighted in #FACC15.
Subtitle in 50% gray: "while my agents handle the rest"
Subtle upward arrow / sunrise visual element in #FACC15 lower-third.
NO frame. NO meta text.
```

## Multi-size handling

Output sizes from visual-system.md drive canvas instruction. The same prompt body runs once per size. For 1024×1536 (carousel), include "Portrait orientation" and shift typography vertical balance toward the top third. For 1024×1792 (story), include "Story format, full-bleed, safe zones top 250px and bottom 350px reserved".

## Anti-patterns

- Mixing palette colors not in the brand's `# Palette` section
- Using stock icon styles when `# Layout` says `icon style: none`
- Adding shadows/gradients when `# Vibe Rules` says `tone: minimal`
- Cropping or "creative" framing when `# Layout` says `negative space: generous`
