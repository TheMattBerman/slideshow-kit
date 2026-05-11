# Suite

User-invocable skills and workflows shipped in this kit.

## `skills/concept-generator/`

Turns brand DNA, trend inputs, and operator notes into carousel concepts and
draft scripts. Use it when the user needs ideas, hooks, angles, or a first
draft before rendering.

Common triggers:

- "generate carousel concepts"
- "turn this trend into a post"
- "draft a carousel script"
- "give me hooks for this brand"

## `skills/styled-carousel/`

Renders a scripted carousel using the brand visual system plus an optional
style preset. It resolves design tokens, builds slide prompts, supports dry
runs, and saves local artifacts for review or publishing.

Common triggers:

- "generate this carousel"
- "render slides for this script"
- "use the founder-notes style"
- "make a LinkedIn carousel"

## Workflows

| Workflow | Use When |
|---|---|
| `workflows/onboard-brand.md` | Create or refresh a brand workspace from supplied voice, positioning, and visual inputs |
| `workflows/daily-loop.md` | Run the repeatable trend-to-carousel loop for a configured brand |
| `workflows/checkin.md` | Collect operator review or hot takes before publishing |

## Composition

The normal path is:

1. Onboard or select a brand.
2. Generate or provide a script.
3. Render with `styled-carousel`.
4. Review local artifacts.
5. Publish only when the brand mode and operator approval allow it.

Brand workspaces, style references, and generated run outputs are user data.
They are intentionally kept out of the public repository.
