# Claude Code Context

Addendum to `AGENTS.md` for Claude Code users.

## Skill Location

When installed, this kit lives at `~/.claude/skills/slideshow-kit/`. The main
entrypoint is `SKILL.md`, which routes into the concept and styled-carousel
workflows.

## Recommended Tool Access

For normal local use, allow:

- `Read`, `Write`, `Edit`
- `Bash(./scripts/*:*)`
- `Bash(python3:*)`
- `Skill(last30)` when you want the daily loop to pull fresh trend inputs

## Invocation Pattern

When a user asks to generate a carousel:

1. Confirm or create the target brand workspace.
2. Read the brand DNA files: `brand-voice.md`, `brand-perspective.md`, and
   `visual-system.md`.
3. Use an existing script, ask for one, or generate one through
   `skills/concept-generator/`.
4. Render the slides with `skills/styled-carousel/`.
5. Save artifacts to the brand run directory before publishing or sharing.

## Public Repo Boundary

Brand workspaces and generated runs are user data. They should stay outside
the public kit repository or under ignored local paths such as `brands/`.
Never commit brand-specific voice files, client assets, generated images,
publish payloads, or local credentials.

## Gotchas

- Run `./doctor.sh` before first use to check local prerequisites.
- `postiz auth:login` is interactive, so the user may need to run it directly.
- Image generation can spend money. Use dry runs while testing and follow the
  live-spend gating rules in `AGENTS.md`.
