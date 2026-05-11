# Agent Instructions

This file provides cross-agent system-prompt context. Every supported agent (Claude Code, Codex, OpenClaw, Hermes) reads this when slideshow-kit is loaded.

## What this kit does

Composes brand-DNA-driven carousel generation with optional daily-loop orchestration. Read `SKILL.md` for routing logic.

## Hard rules

1. **Live-spend gating.** New brands default to `mode: "draft"` for first 7 daily runs. Image generation never runs without `--confirm-spend` outside of the daily loop's gated flow.
2. **Save-first.** Generated images get downloaded to local disk immediately. Never reference an ephemeral provider URL as the canonical artifact.
3. **Decoupling.** Telegram failures never block postiz publishing. Postiz failures never block Telegram alerts.
4. **No fabrication.** When extracting brand DNA from interviews, never invent specifics the user didn't provide. Use clearly-marked placeholders (`<TODO: confirm with user>`).
5. **No XML tags in skill bodies.** Use markdown headings only. References stay one level deep (no chained imports).

## Cross-agent invocation

When this kit's daily-loop workflow says "invoke last30 skill," each agent uses its native skill mechanism:
- Claude Code: `Skill` tool
- Codex: skill invocation per Codex docs
- OpenClaw: skill ref in workflow
- Hermes: plugin call

## Conventions

- All bash: `set -euo pipefail`
- Paths: forward slashes only
- Dates: ISO 8601 (`YYYY-MM-DD`)
- Brand workspaces: external to kit at `~/.clawd/brands/<slug>/`
- Logs: per-run dir at `~/.clawd/brands/<slug>/runs/<date>/`
