#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(git rev-parse --show-toplevel)"
}

_make_brand() {
  local slug="$1"
  local brand_dir="$BATS_TMPDIR/brands/$slug"
  local style_dir="$brand_dir/styles/social_native"
  mkdir -p "$style_dir/refs"
  cat > "$brand_dir/visual-system.md" <<EOF
---
palette:
  background: "#FFFFFF"
---
EOF
  cat > "$style_dir/DESIGN.md" <<EOF
---
palette:
  background: "#FFFFFF"
---

# Style: Test
EOF
  echo "$brand_dir"
}

@test "styled-carousel: numbered_diagnostic renders 7 slides" {
  brand_dir=$(_make_brand "ndtest")
  run_dir="$BATS_TMPDIR/runs/nd-$$"
  mkdir -p "$run_dir"
  cp "$REPO_ROOT/tests/fixtures/formats/numbered_diagnostic_ok.md" "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand ndtest \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q '"format_name": "numbered_diagnostic"' "$run_dir/output-log.json"
  grep -q '"slide_count": 7' "$run_dir/output-log.json"
  grep -q '"close_action": "save"' "$run_dir/output-log.json"
}

@test "styled-carousel: each of the seven formats renders dry-run" {
  for fmt in narrative numbered_diagnostic receipt_context process_reveal anatomy_breakdown before_after counter_narrative; do
    brand_dir=$(_make_brand "fmt-$fmt")
    run_dir="$BATS_TMPDIR/runs/$fmt-$$"
    mkdir -p "$run_dir"
    cp "$REPO_ROOT/tests/fixtures/formats/${fmt}_ok.md" "$run_dir/script.md"

    run python skills/styled-carousel/scripts/generate_styled_carousel.py \
      --brand "fmt-$fmt" \
      --brands-root "$BATS_TMPDIR/brands" \
      --style social_native \
      --script "$run_dir/script.md" \
      --output "$run_dir" \
      --dry-run

    [ "$status" -eq 0 ]
    grep -q "\"format_name\": \"$fmt\"" "$run_dir/output-log.json"
  done
}

@test "styled-carousel: missing frontmatter defaults to narrative" {
  brand_dir=$(_make_brand "noframe")
  run_dir="$BATS_TMPDIR/runs/noframe-$$"
  mkdir -p "$run_dir"
  cp "$REPO_ROOT/tests/fixtures/formats/no_frontmatter.md" "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand noframe \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q '"format_name": "narrative"' "$run_dir/output-log.json"
}

@test "styled-carousel: --no-format-check bypasses violations" {
  brand_dir=$(_make_brand "bypass")
  run_dir="$BATS_TMPDIR/runs/bypass-$$"
  mkdir -p "$run_dir"
  cp "$REPO_ROOT/tests/fixtures/formats/bad_close.md" "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand bypass \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --no-format-check \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q '"format_check_skipped": true' "$run_dir/output-log.json"
}

@test "styled-carousel: bad_close fails without --no-format-check" {
  brand_dir=$(_make_brand "badclose")
  run_dir="$BATS_TMPDIR/runs/badclose-$$"
  mkdir -p "$run_dir"
  cp "$REPO_ROOT/tests/fixtures/formats/bad_close.md" "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand badclose \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -ne 0 ]
  echo "$output" | grep -q 'format_close_missing_action'
}

@test "styled-carousel: unknown_format fails with format_unknown_format" {
  brand_dir=$(_make_brand "ufmt")
  run_dir="$BATS_TMPDIR/runs/ufmt-$$"
  mkdir -p "$run_dir"
  cp "$REPO_ROOT/tests/fixtures/formats/unknown_format.md" "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand ufmt \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -ne 0 ]
  echo "$output" | grep -qE 'unknown format|format_unknown_format'
}

@test "styled-carousel: bad_count fails with format_missing_slot" {
  brand_dir=$(_make_brand "badcnt")
  run_dir="$BATS_TMPDIR/runs/badcnt-$$"
  mkdir -p "$run_dir"
  cp "$REPO_ROOT/tests/fixtures/formats/bad_count.md" "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand badcnt \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -ne 0 ]
  echo "$output" | grep -qE 'format_missing_slot|ITEM'
}
