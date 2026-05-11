#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(git rev-parse --show-toplevel)"
}

@test "generate_concepts: rich brand happy path writes concepts.md" {
  TMP="$BATS_TMPDIR/gc-rich-$$"
  mkdir -p "$TMP/brands/rich"
  cp "$REPO_ROOT/tests/fixtures/corpus/rich_brand/voice-profile.md" "$TMP/brands/rich/"
  cp "$REPO_ROOT/tests/fixtures/corpus/rich_brand/brand-voice.md" "$TMP/brands/rich/"
  mkdir -p "$TMP/brands/rich/deliverables/recent"
  cp -r "$REPO_ROOT/tests/fixtures/corpus/rich_brand/deliverables/recent/." \
        "$TMP/brands/rich/deliverables/recent/"
  mkdir -p "$TMP/run"
  echo "trend research content" > "$TMP/run/checkin-response.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/skills/concept-generator/scripts/generate_concepts.sh" \
    --brand rich \
    --trend-input "$TMP/run/checkin-response.md" \
    --output "$TMP/run/" \
    --dry-run

  [ "$status" -eq 0 ]
  [ -f "$TMP/run/concepts.md" ]
  grep -q "## Concept" "$TMP/run/concepts.md"

  rm -rf "$TMP"
}

@test "generate_concepts: thin brand happy path uses defaults" {
  TMP="$BATS_TMPDIR/gc-thin-$$"
  mkdir -p "$TMP/brands/thin"
  echo "# voice" > "$TMP/brands/thin/brand-voice.md"
  mkdir -p "$TMP/run"
  echo "trend" > "$TMP/run/checkin-response.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/skills/concept-generator/scripts/generate_concepts.sh" \
    --brand thin \
    --trend-input "$TMP/run/checkin-response.md" \
    --output "$TMP/run/" \
    --dry-run

  [ "$status" -eq 0 ]
  [ -f "$TMP/run/concepts.md" ]

  rm -rf "$TMP"
}

@test "generate_concepts: missing brand exits non-zero" {
  TMP="$BATS_TMPDIR/gc-missing-$$"
  mkdir -p "$TMP/brands" "$TMP/run"
  echo "trend" > "$TMP/run/checkin-response.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/skills/concept-generator/scripts/generate_concepts.sh" \
    --brand nonexistent \
    --trend-input "$TMP/run/checkin-response.md" \
    --output "$TMP/run/"

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'not found'

  rm -rf "$TMP"
}

@test "generate_concepts: missing trend-input exits non-zero" {
  TMP="$BATS_TMPDIR/gc-notrend-$$"
  mkdir -p "$TMP/brands/anybrand" "$TMP/run"
  echo "# voice" > "$TMP/brands/anybrand/brand-voice.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/skills/concept-generator/scripts/generate_concepts.sh" \
    --brand anybrand \
    --trend-input "$TMP/run/missing.md" \
    --output "$TMP/run/"

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'trend.*not found\|not found.*trend'

  rm -rf "$TMP"
}

@test "generate_concepts: --count override emits count value" {
  TMP="$BATS_TMPDIR/gc-count-$$"
  mkdir -p "$TMP/brands/cnt" "$TMP/run"
  echo "# voice" > "$TMP/brands/cnt/brand-voice.md"
  echo "trend" > "$TMP/run/checkin-response.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/skills/concept-generator/scripts/generate_concepts.sh" \
    --brand cnt \
    --trend-input "$TMP/run/checkin-response.md" \
    --output "$TMP/run/" \
    --count 5 \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q '"count": 5' "$TMP/run/concept-context.json"

  rm -rf "$TMP"
}

@test "generate_concepts: --mode autopilot emits mode value" {
  TMP="$BATS_TMPDIR/gc-mode-$$"
  mkdir -p "$TMP/brands/mb" "$TMP/run"
  echo "# voice" > "$TMP/brands/mb/brand-voice.md"
  echo "trend" > "$TMP/run/checkin-response.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/skills/concept-generator/scripts/generate_concepts.sh" \
    --brand mb \
    --trend-input "$TMP/run/checkin-response.md" \
    --output "$TMP/run/" \
    --mode autopilot \
    --dry-run

  [ "$status" -eq 0 ]
  grep -q '"mode": "autopilot"' "$TMP/run/concept-context.json"

  rm -rf "$TMP"
}

@test "generate_concepts: oversized trend-input exits non-zero" {
  TMP="$BATS_TMPDIR/gc-big-$$"
  mkdir -p "$TMP/brands/big" "$TMP/run"
  echo "# voice" > "$TMP/brands/big/brand-voice.md"
  head -c 300000 /dev/urandom | base64 > "$TMP/run/big-trend.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/skills/concept-generator/scripts/generate_concepts.sh" \
    --brand big \
    --trend-input "$TMP/run/big-trend.md" \
    --output "$TMP/run/" \
    --dry-run

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'exceeds.*bytes'

  rm -rf "$TMP"
}
