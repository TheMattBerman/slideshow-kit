#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  export SLIDESHOW_BRANDS_ROOT="$TEST_HOME/brands"
  cd "$BATS_TEST_DIRNAME/.."
}

teardown() { rm -rf "$TEST_HOME"; }

@test "doctor.sh exits 1 when no agents installed" {
  run ./doctor.sh
  [ "$status" -eq 1 ]
  [[ "$output" =~ "FAIL" ]]
}

@test "doctor.sh exits 0 when one agent path exists" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  run ./doctor.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "PASS" ]]
}

@test "doctor.sh reports per-brand health" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/matt"
  for f in brand-voice brand-perspective visual-system; do
    echo "---" > "$SLIDESHOW_BRANDS_ROOT/matt/$f.md"
  done
  run ./doctor.sh
  [[ "$output" =~ "matt" ]]
}

@test "doctor.sh checks for ImageMagick (magick or convert)" {
    run grep -E "command -v (magick|convert)" doctor.sh
    [ "$status" -eq 0 ]
}

@test "doctor.sh mentions imagemagick install hint" {
    run grep -E "brew install imagemagick" doctor.sh
    [ "$status" -eq 0 ]
}

@test "doctor.sh WARNs when brand is autopilot with runs_history < 7" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/young-autopilot"
  for f in brand-voice brand-perspective visual-system; do
    echo "---" > "$SLIDESHOW_BRANDS_ROOT/young-autopilot/$f.md"
  done
  cat > "$SLIDESHOW_BRANDS_ROOT/young-autopilot/config.json" <<'JSON'
{"brand":"young-autopilot","mode":"autopilot","runs_history":2,"postiz":{"integration_ids":["x"]},"checkin":{"channel":"agent","timeout_minutes":30,"telegram_chat_id":null},"formats":["branded"],"lookback_days":7,"posts_per_day":1,"created_on":"2026-05-04"}
JSON
  run ./doctor.sh
  grep -q "young-autopilot.*autopilot.*runs of history" <<< "$output"
}

@test "doctor.sh does NOT warn when brand is autopilot with runs_history >= 7" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/old-autopilot"
  for f in brand-voice brand-perspective visual-system; do
    echo "---" > "$SLIDESHOW_BRANDS_ROOT/old-autopilot/$f.md"
  done
  cat > "$SLIDESHOW_BRANDS_ROOT/old-autopilot/config.json" <<'JSON'
{"brand":"old-autopilot","mode":"autopilot","runs_history":42,"postiz":{"integration_ids":["x"]},"checkin":{"channel":"agent","timeout_minutes":30,"telegram_chat_id":null},"formats":["branded"],"lookback_days":7,"posts_per_day":1,"created_on":"2026-04-01"}
JSON
  run ./doctor.sh
  ! grep -q "old-autopilot.*autopilot.*runs of history" <<< "$output"
}

@test "doctor.sh does NOT warn when brand is in draft mode regardless of runs_history" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/draft-newbie"
  for f in brand-voice brand-perspective visual-system; do
    echo "---" > "$SLIDESHOW_BRANDS_ROOT/draft-newbie/$f.md"
  done
  cat > "$SLIDESHOW_BRANDS_ROOT/draft-newbie/config.json" <<'JSON'
{"brand":"draft-newbie","mode":"draft","runs_history":0,"postiz":{"integration_ids":["x"]},"checkin":{"channel":"agent","timeout_minutes":30,"telegram_chat_id":null},"formats":["branded"],"lookback_days":7,"posts_per_day":1,"created_on":"2026-05-04"}
JSON
  run ./doctor.sh
  ! grep -q "draft-newbie.*autopilot.*runs of history" <<< "$output"
}

@test "doctor.sh warns when a brand has no styles/ dir" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/no_styles"
  echo '{"brand":"no_styles"}' > "$SLIDESHOW_BRANDS_ROOT/no_styles/config.json"
  run ./doctor.sh
  echo "$output" | grep -qi "no_styles.*styles\|styles.*no_styles"
}

@test "doctor.sh warns when brand visual-system.md is prose-shaped" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/proseboi/styles/social_native"
  # Prose-shaped visual-system.md (no YAML frontmatter; first line is not `---`).
  cat > "$SLIDESHOW_BRANDS_ROOT/proseboi/visual-system.md" <<'EOF'
# Visual System

## Palette
- Background: #0D1117
EOF
  # Other DNA files present so the FAIL on missing files doesn't fire.
  echo "stub" > "$SLIDESHOW_BRANDS_ROOT/proseboi/brand-voice.md"
  echo "stub" > "$SLIDESHOW_BRANDS_ROOT/proseboi/brand-perspective.md"
  # A style DESIGN.md so the styles-dir check passes too.
  printf -- "---\n---\n" > "$SLIDESHOW_BRANDS_ROOT/proseboi/styles/social_native/DESIGN.md"

  run ./doctor.sh

  # Non-fatal: status should still be 0 (after agent install stub).
  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] brand proseboi: visual-system.md is prose-shaped" ]]
  [[ "$output" =~ "migrate_brand_visual_system.sh" ]]
}

@test "doctor.sh warns when brand visual-system.md is hybrid-shaped (no visual tokens)" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/hybridboi/styles/social_native"
  cat > "$SLIDESHOW_BRANDS_ROOT/hybridboi/visual-system.md" <<'EOF'
---
brand: hybridboi
last-updated: 2026-05-04
---

# Palette
- Background: #0D1117
EOF
  echo "stub" > "$SLIDESHOW_BRANDS_ROOT/hybridboi/brand-voice.md"
  echo "stub" > "$SLIDESHOW_BRANDS_ROOT/hybridboi/brand-perspective.md"
  printf -- "---\n---\n" > "$SLIDESHOW_BRANDS_ROOT/hybridboi/styles/social_native/DESIGN.md"

  run ./doctor.sh

  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] brand hybridboi: visual-system.md is missing visual-token frontmatter" ]]
}

@test "doctor.sh warns on em-dash in brand-voice.md" {
  mkdir -p "$HOME/.claude/skills/slideshow-kit"
  echo "stub" > "$HOME/.claude/skills/slideshow-kit/SKILL.md"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/dasherbrand/styles/social_native"
  printf -- "---\n---\n" > "$SLIDESHOW_BRANDS_ROOT/dasherbrand/visual-system.md"
  printf "# voice\n\nlowercase only \xe2\x80\x94 and punchy.\n" \
    > "$SLIDESHOW_BRANDS_ROOT/dasherbrand/brand-voice.md"
  echo "stub" > "$SLIDESHOW_BRANDS_ROOT/dasherbrand/brand-perspective.md"
  printf -- "---\n---\n" > "$SLIDESHOW_BRANDS_ROOT/dasherbrand/styles/social_native/DESIGN.md"

  run ./doctor.sh

  [ "$status" -eq 0 ]
  [[ "$output" =~ "[WARN] brand dasherbrand: brand-voice.md violates em_dash" ]]
}
