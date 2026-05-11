# Carousel examples (operator-supplied)

This directory holds operator-supplied annotated carousel reference material.
The concept-generator skill loads any markdown files dropped here as
additional pattern context, layered on top of the kit-shipped
`references/concept-patterns/`.

## What to drop here

- Annotated winners: high-bookmark carousels with structural notes (what
  hook style, what format, why it saved)
- Annotated losers: low-bookmark or "AI tell"-shaped carousels with notes
  on what failed
- Pattern names matching the kit-shipped concept patterns when applicable;
  add new pattern names freely when none apply

## Schema (loose)

Each markdown file should have:

- A `# Title` line naming the carousel
- A `## Outcome` section with bookmark/save metrics if known
- A `## Pattern` section listing the format, hook style, structural pattern
- A `## Why it worked` (or `## Why it failed`) section
- The original carousel slide content for the agent to reference

## Status

Empty in v0.8.0 default install. Matt is preparing an annotated batch.
Once added, the skill will load these automatically; no kit-side change
required.
