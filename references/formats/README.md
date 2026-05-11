# Carousel Formats

Slideshow-kit ships seven carousel formats. Each is a declarative YAML slot
template loaded by `lib/format_registry.py`. Operators select a format via
YAML frontmatter on the script file:

```yaml
---
format: numbered_diagnostic
close_action: save
---
```

Missing frontmatter falls back to `format: narrative`, `close_action: save`
(narrative's default).

## The seven formats

| Format | Slot sequence | Use case |
|---|---|---|
| `narrative` | HOOK -> REVEAL -> SETUP -> EXAMPLES -> OUTCOME -> CTA | Default. Story-driven case studies. |
| `numbered_diagnostic` | HOOK -> ITEM (2-8) -> FIX -> CTA | "The N tells", "5 reasons your X is broken". |
| `receipt_context` | HOOK -> RECEIPT -> BREAKDOWN -> CONTEXT -> CTA | "Look what they said" + your interpretation. |
| `process_reveal` | HOOK -> STEP (3-7) -> OUTCOME -> CTA | "How I did X in N minutes". |
| `anatomy_breakdown` | HOOK -> SAMPLE (2-4) -> ANALYSIS -> PATTERNS -> CTA | Teardowns, "anatomy of a winning X". |
| `before_after` | HOOK -> BEFORE -> AFTER -> DELTA -> CTA | Transformations, results comparisons. |
| `counter_narrative` | HOOK -> THE_QUOTE -> THE_QUESTION -> THE_REAL_ANSWER -> CTA | "Industry says X; here's why X is wrong". |

## Slot heading aliases

The format-aware parser matches the first uppercase word of each `# HEADING`
against the slot's `aliases` list. Aliases are case-insensitive. Headings may
include trailing title text (`# TELL #1: it has 6 slides` matches the ITEM
slot in numbered_diagnostic via the TELL alias).

See each format's YAML for its alias list.

## Word counts

Each slot declares a `word_count_range`. Hook slots are tight (6-15). Body
slots are wider (15-50 typical, up to 60 for receipt and analysis). Close
slots are 10-50 to accommodate two-beat closes (payoff + CTA).

## Close actions

Every script declares `close_action: save | share | comment | soft`.
- `save`: the close slide must contain save vocabulary ("save", "bookmark",
  "screenshot", "come back to").
- `share`: must contain share vocabulary ("share", "send", "tag", etc.).
- `comment`: must contain comment vocabulary ("comment", "drop", etc.).
- `soft`: no vocabulary required; close is observational.

Brand-specific vocab can be added in `brands/<slug>/brand-voice.md` under
`## Close vocabulary` sub-sections.

## Authoring a new format

Currently formats are kit-level only. To add a new format, drop a YAML file
in this directory matching the schema (see existing files). It must:

- Have `name:` matching the filename stem.
- Define a non-empty `slots:` list.
- First slot's role should be HOOK (parser-friendly convention).
- Last slot's role should be CTA (close-action checking applies here).
- Each slot has either `count:` or `count_range:` plus `word_count_range:`.
- `default_close_action:` must be `save`, `share`, `comment`, or `soft`.

The format will load automatically; `list_formats()` enumerates the directory.
