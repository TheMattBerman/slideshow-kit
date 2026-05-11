#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "fake" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  cd "$BATS_TEST_DIRNAME/.."
}

teardown() {
  rm -rf "$TEST_HOME"
}

@test "uninstall.sh removes kit from ~/.claude/skills" {
  run ./uninstall.sh --yes
  [ "$status" -eq 0 ]
  [ ! -d "$HOME/.claude/skills/slideshow-kit" ]
}

@test "uninstall.sh preserves ~/.clawd/brands by default" {
  mkdir -p "$HOME/.clawd/brands/matt"
  echo "voice" > "$HOME/.clawd/brands/matt/brand-voice.md"
  run ./uninstall.sh --yes
  [ -d "$HOME/.clawd/brands/matt" ]
  [ -f "$HOME/.clawd/brands/matt/brand-voice.md" ]
}
