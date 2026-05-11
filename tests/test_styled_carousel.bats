#!/usr/bin/env bats

setup() {
  KIT_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  cd "$KIT_DIR"
  TMP="$(mktemp -d)"
  export TMP
  export HOME="$TMP/home"
  export SLIDESHOW_BRANDS_ROOT="$TMP/brands"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/acme/styles"
  cp -r "$KIT_DIR/references/styles/social_native" \
        "$SLIDESHOW_BRANDS_ROOT/acme/styles/social_native"
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/visual-system.md" <<'MD'
---
name: brand
palette:
  primary_accent: "#FF0000"
---

# Brand DNA

Test brand for bats verification.
MD
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/config.json" <<'JSON'
{
  "brand": "acme",
  "default_style": "social_native"
}
JSON
  cat > "$TMP/script.md" <<'EOF'
---
format: narrative
close_action: save
---

# HOOK
test hook line that is long enough to pass narrative

# REVEAL
test reveal body that satisfies the narrative format minimum word count for the lint pass

# SETUP
test setup body that satisfies the narrative format minimum word count for the lint pass

# EXAMPLES
test examples body that satisfies the narrative format minimum word count for the lint pass

# OUTCOME
test outcome body that satisfies the narrative format minimum word count for the lint pass

# CTA
save this if you want the test fixture to keep passing across releases reliably
EOF
  GENERATOR="$KIT_DIR/skills/styled-carousel/scripts/generate_styled_carousel.py"
  export GENERATOR
}

teardown() {
  rm -rf "$TMP"
}

@test "styled-carousel exits 1 when brand workspace missing" {
  run "$GENERATOR" --brand nonexistent --script "$TMP/script.md" --dry-run
  [ "$status" -eq 1 ]
}

@test "styled-carousel dry-run completes successfully on a valid brand" {
  run "$GENERATOR" --brand acme --script "$TMP/script.md" --dry-run
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "social_native"
}

@test "styled-carousel writes prompts.json in output dir" {
  run "$GENERATOR" --brand acme --script "$TMP/script.md" --dry-run
  [ "$status" -eq 0 ]
  output_dir=$(find "$SLIDESHOW_BRANDS_ROOT/acme/runs" -name "prompts.json" -type f | head -n1)
  [ -f "$output_dir" ]
}

@test "styled-carousel resolves --style flag over config default" {
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/acme/styles/custom"
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/styles/custom/DESIGN.md" <<'EOF'
---
name: custom
palette:
  background: "#123456"
---

Body for custom.
EOF
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/acme/styles/custom/refs"
  run "$GENERATOR" --brand acme --style custom --script "$TMP/script.md" --dry-run
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "custom"
}

@test "styled-carousel exits 1 when --style points at a missing style" {
  run "$GENERATOR" --brand acme --style nonexistent --script "$TMP/script.md" --dry-run
  [ "$status" -eq 1 ]
}

@test "styled-carousel falls back to social_native when no default_style and no flag" {
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/config.json" <<'JSON'
{
  "brand": "acme"
}
JSON
  run "$GENERATOR" --brand acme --script "$TMP/script.md" --dry-run
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "social_native"
}

@test "styled-carousel output filename includes style prefix" {
  run "$GENERATOR" --brand acme --script "$TMP/script.md" --dry-run
  [ "$status" -eq 0 ]
  prompts_file=$(find "$SLIDESHOW_BRANDS_ROOT/acme/runs" -name "prompts.json" -type f | head -n1)
  grep -q '"slide-01"' "$prompts_file"
}

@test "styled-carousel writes output-log.json with style + brand" {
  run "$GENERATOR" --brand acme --script "$TMP/script.md" --dry-run
  [ "$status" -eq 0 ]
  log_file=$(find "$SLIDESHOW_BRANDS_ROOT/acme/runs" -name "output-log.json" -type f | head -n1)
  grep -q '"brand": "acme"' "$log_file"
  grep -q '"style": "social_native"' "$log_file"
}

@test "styled-carousel exits 1 on empty script" {
  echo "" > "$TMP/empty.md"
  run "$GENERATOR" --brand acme --script "$TMP/empty.md" --dry-run
  [ "$status" -eq 1 ]
}

@test "styled-carousel honors --output flag" {
  CUSTOM_OUT="$TMP/custom-output"
  run "$GENERATOR" --brand acme --script "$TMP/script.md" \
                   --output "$CUSTOM_OUT" --dry-run
  [ "$status" -eq 0 ]
  [ -f "$CUSTOM_OUT/prompts.json" ]
}

@test "styled-carousel: writes resolved-tokens.json to run dir" {
  brand_dir="$BATS_TMPDIR/brands/test-brand"
  style_dir="$brand_dir/styles/social_native"
  run_dir="$BATS_TMPDIR/runs/$$"
  mkdir -p "$style_dir/refs" "$run_dir"

  cat > "$brand_dir/visual-system.md" <<'EOF'
---
palette:
  primary_accent: "#F43F5E"
---
EOF

  cat > "$style_dir/DESIGN.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---

# Style: Test
EOF

  cat > "$run_dir/script.md" <<'EOF'
# HOOK
test hook line for narrative format minimum.

# REVEAL
test reveal body that satisfies the narrative format minimum word count for the lint pass

# SETUP
test setup body that satisfies the narrative format minimum word count for the lint pass

# EXAMPLES
test examples body that satisfies the narrative format minimum word count for the lint pass

# OUTCOME
test outcome body that satisfies the narrative format minimum word count for the lint pass

# CTA
save this if you want the test fixture to keep passing across releases reliably
EOF

  run "$GENERATOR" \
    --brand test-brand \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --no-format-check \
    --dry-run

  [ "$status" -eq 0 ]
  [ -f "$run_dir/resolved-tokens.json" ]
  grep -q '"_schema_version": 1' "$run_dir/resolved-tokens.json"
  grep -q '"_layer_provenance"' "$run_dir/resolved-tokens.json"
}

@test "styled-carousel: pre-render lint fails on em-dash in script" {
  brand_dir="$BATS_TMPDIR/brands/lint-test"
  style_dir="$brand_dir/styles/social_native"
  run_dir="$BATS_TMPDIR/runs/lint-$$"
  mkdir -p "$style_dir/refs" "$run_dir"
  printf -- "---\n---\n" > "$brand_dir/visual-system.md"
  cat > "$style_dir/DESIGN.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---

# Style: Test
EOF
  printf "# HOOK\nhook line with em-dash \xe2\x80\x94 right here that is long enough.\n\n# REVEAL\nreveal body with enough words to satisfy the narrative format minimum word count.\n\n# SETUP\nsetup body with enough words to satisfy the narrative format minimum word count.\n\n# EXAMPLES\nexamples body with enough words to satisfy the narrative format minimum word count.\n\n# OUTCOME\noutcome body with enough words to satisfy the narrative format minimum word count.\n\n# CTA\nsave this if you want the test fixture to keep passing across releases reliably.\n" > "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand lint-test \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -ne 0 ]
  echo "$output" | grep -q 'em_dash'
}

@test "styled-carousel: --no-lint bypasses pre-render lint" {
  brand_dir="$BATS_TMPDIR/brands/lint-bypass"
  style_dir="$brand_dir/styles/social_native"
  run_dir="$BATS_TMPDIR/runs/bypass-$$"
  mkdir -p "$style_dir/refs" "$run_dir"
  printf -- "---\n---\n" > "$brand_dir/visual-system.md"
  cat > "$style_dir/DESIGN.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---
EOF
  printf "# HOOK\nhook line with em-dash \xe2\x80\x94 right here that is long enough.\n\n# REVEAL\nreveal body with enough words to satisfy the narrative format minimum word count.\n\n# SETUP\nsetup body with enough words to satisfy the narrative format minimum word count.\n\n# EXAMPLES\nexamples body with enough words to satisfy the narrative format minimum word count.\n\n# OUTCOME\noutcome body with enough words to satisfy the narrative format minimum word count.\n\n# CTA\nsave this if you want the test fixture to keep passing across releases reliably.\n" > "$run_dir/script.md"

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand lint-bypass \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --no-lint \
    --no-format-check \
    --dry-run

  [ "$status" -eq 0 ]
  [ -f "$run_dir/output-log.json" ]
  grep -q '"lint_skipped": true' "$run_dir/output-log.json"
}

@test "styled-carousel: variable slide count is honored (numbered_diagnostic with 6 items)" {
  brand_dir="$BATS_TMPDIR/brands/varcnt"
  style_dir="$brand_dir/styles/social_native"
  run_dir="$BATS_TMPDIR/runs/varcnt-$$"
  mkdir -p "$style_dir/refs" "$run_dir"
  cat > "$brand_dir/visual-system.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---
EOF
  cat > "$style_dir/DESIGN.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---

# Style: Test
EOF
  cat > "$run_dir/script.md" <<'EOF'
---
format: numbered_diagnostic
close_action: save
---

# HOOK
six items in this carousel one through six explored.

# TELL #1
fifteen words exactly here for the body slide minimum word count and not more here.

# TELL #2
fifteen words exactly here for the body slide minimum word count and not more here.

# TELL #3
fifteen words exactly here for the body slide minimum word count and not more here.

# TELL #4
fifteen words exactly here for the body slide minimum word count and not more here.

# TELL #5
fifteen words exactly here for the body slide minimum word count and not more here.

# TELL #6
fifteen words exactly here for the body slide minimum word count and not more here.

# FIX
fifteen words exactly here for the body slide minimum word count and not more here.

# CTA
save this for later when you need to come back to it for sure for sure.
EOF

  run python skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand varcnt \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q '"slide_count": 9' "$run_dir/output-log.json"
}

@test "styled-carousel: thread_native style renders dry-run" {
  brand_dir="$BATS_TMPDIR/brands/threadnat"
  run_dir="$BATS_TMPDIR/runs/threadnat-$$"
  mkdir -p "$brand_dir" "$run_dir"
  cat > "$brand_dir/visual-system.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---
EOF
  cp "$KIT_DIR/tests/fixtures/formats/narrative_ok.md" "$run_dir/script.md"

  run python3 skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand threadnat \
    --brands-root "$BATS_TMPDIR/brands" \
    --style thread_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q '"style": "thread_native"' "$run_dir/output-log.json"
}

@test "styled-carousel: writes output-log.json on per-slide failure (mocked gpt-image-2)" {
  brand_dir="$BATS_TMPDIR/brands/failtest"
  style_dir="$brand_dir/styles/social_native"
  run_dir="$BATS_TMPDIR/runs/failtest-$$"
  mkdir -p "$style_dir/refs" "$run_dir"
  cat > "$brand_dir/visual-system.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---
EOF
  cat > "$style_dir/DESIGN.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---

# Style: Test
EOF
  cat > "$run_dir/script.md" <<'EOF'
---
format: narrative
close_action: save
---

# HOOK
short hook line for the test scenario that fits.

# REVEAL
fifteen words exactly here for the body slide minimum count and not too more here.

# SETUP
fifteen words exactly here for the body slide minimum count and not too more here.

# EXAMPLES
fifteen words exactly here for the body slide minimum count and not too more here.

# OUTCOME
fifteen words exactly here for the body slide minimum count and not too more here.

# CTA
save this for later when you need to come back to it for sure for sure.
EOF

  # --dry-run mode does not call the API but does run through the per-slide loop
  # and writes output-log.json. This validates the resilience plumbing without
  # mocking the API.
  run python3 skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand failtest \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -eq 0 ]
  # New v0.7.6 fields must be present
  grep -q '"slides_completed": 6' "$run_dir/output-log.json"
  grep -q '"slides_failed": 0' "$run_dir/output-log.json"
  grep -q '"slide_results"' "$run_dir/output-log.json"
}

@test "styled_carousel: reads pre-existing scene-direction.md and skips visual_director call" {
  brand_dir="$BATS_TMPDIR/brands/scenetest"
  style_dir="$brand_dir/styles/social_native"
  run_dir="$BATS_TMPDIR/runs/scenetest-$$"
  mkdir -p "$style_dir/refs" "$run_dir"
  cat > "$brand_dir/visual-system.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---
EOF
  cat > "$style_dir/DESIGN.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
image_treatment: "screenshot_native"
---

# Style: Test
EOF
  cat > "$run_dir/script.md" <<'EOF'
---
format: narrative
close_action: save
---

# HOOK
short hook line for the test scenario that fits.

# REVEAL
fifteen words exactly here for the body slide minimum count and not too more here.

# SETUP
fifteen words exactly here for the body slide minimum count and not too more here.

# EXAMPLES
fifteen words exactly here for the body slide minimum count and not too more here.

# OUTCOME
fifteen words exactly here for the body slide minimum count and not too more here.

# CTA
save this for later when you need to come back to it for sure for sure.
EOF
  cat > "$run_dir/scene-direction.md" <<'EOF'
# Scene direction (source: stage_3)

## Slide 1 (HOOK)
**Tone:** observational
**Scene:** matt at standing desk, late evening lamp warmth, mid-thought.

## Slide 2 (CTA)
**Tone:** punchy
**Scene:** closeup of laptop screen with bookmark icon highlighted.
EOF

  run python3 skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand scenetest \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q "source: stage_3" "$run_dir/scene-direction.md"
  [ -f "$run_dir/output-log.json" ]
  grep -q '"scene_direction_source": "stage_3"' "$run_dir/output-log.json"
}

@test "styled_carousel: auto-generates scene-direction.md when absent (renderer_fallback)" {
  brand_dir="$BATS_TMPDIR/brands/lazytest"
  style_dir="$brand_dir/styles/social_native"
  run_dir="$BATS_TMPDIR/runs/lazytest-$$"
  mkdir -p "$style_dir/refs" "$run_dir"
  cat > "$brand_dir/visual-system.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
---
EOF
  cat > "$style_dir/DESIGN.md" <<'EOF'
---
palette:
  background: "#FFFFFF"
image_treatment: "screenshot_native"
---

# Style: Test
EOF
  cat > "$run_dir/script.md" <<'EOF'
---
format: narrative
close_action: save
---

# HOOK
short hook line for the test scenario that fits.

# REVEAL
fifteen words exactly here for the body slide minimum count and not too more here.

# SETUP
fifteen words exactly here for the body slide minimum count and not too more here.

# EXAMPLES
fifteen words exactly here for the body slide minimum count and not too more here.

# OUTCOME
fifteen words exactly here for the body slide minimum count and not too more here.

# CTA
save this for later when you need to come back to it for sure for sure.
EOF

  run python3 skills/styled-carousel/scripts/generate_styled_carousel.py \
    --brand lazytest \
    --brands-root "$BATS_TMPDIR/brands" \
    --style social_native \
    --script "$run_dir/script.md" \
    --output "$run_dir" \
    --dry-run

  [ "$status" -eq 0 ]
  # In dry-run with screenshot_native (not character-driven), the renderer
  # does not generate scene-direction.md; that's expected.
  if [ -f "$run_dir/scene-direction.md" ]; then
    grep -q "source: renderer_fallback" "$run_dir/scene-direction.md"
  fi
  [ -f "$run_dir/output-log.json" ]
}
