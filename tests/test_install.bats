#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  mkdir -p "$HOME/.claude/skills" "$HOME/.codex/skills"
  cd "$BATS_TEST_DIRNAME/.."
}

teardown() {
  rm -rf "$TEST_HOME"
}

@test "install.sh detects ~/.claude/skills and copies kit" {
  run ./install.sh --no-postiz-auth --no-deps-check
  [ "$status" -eq 0 ]
  [ -d "$HOME/.claude/skills/slideshow-kit" ]
  [ -f "$HOME/.claude/skills/slideshow-kit/SKILL.md" ]
}

@test "install.sh detects ~/.codex/skills and copies kit" {
  run ./install.sh --no-postiz-auth --no-deps-check
  [ "$status" -eq 0 ]
  [ -d "$HOME/.codex/skills/slideshow-kit" ]
}

@test "install.sh exits 1 when no agent paths detected" {
  rm -rf "$HOME/.claude" "$HOME/.codex"
  run ./install.sh --no-postiz-auth --no-deps-check
  [ "$status" -eq 1 ]
  [[ "$output" =~ "no supported agent paths detected" ]]
}

@test "install.sh creates ~/.clawd/slideshow-kit/config.json" {
  run ./install.sh --no-postiz-auth --no-deps-check
  [ "$status" -eq 0 ]
  [ -f "$HOME/.clawd/slideshow-kit/config.json" ]
}
