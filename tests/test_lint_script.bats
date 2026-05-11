#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  TMP="$BATS_TMPDIR/lint-$$"
  mkdir -p "$TMP"
}

teardown() {
  rm -rf "$TMP"
}

@test "lint_script: clean file exits 0 silently" {
  cat > "$TMP/clean.md" <<'EOF'
hook: this is a clean line.
body: nothing here violates.
close: save this.
EOF

  run "$REPO_ROOT/scripts/lint_script.sh" "$TMP/clean.md"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "lint_script: em-dash exits 1 with file:line:col" {
  printf 'a \xe2\x80\x94 b\n' > "$TMP/dirty.md"

  run "$REPO_ROOT/scripts/lint_script.sh" "$TMP/dirty.md"
  [ "$status" -eq 1 ]
  echo "$output" | grep -qE "$TMP/dirty.md:1:[0-9]+ \[em_dash\]"
}

@test "lint_script: --brand picks up brand-voice ## Avoid" {
  mkdir -p "$TMP/brands/test-brand"
  cat > "$TMP/brands/test-brand/brand-voice.md" <<'EOF'
# voice

## Avoid
- "circle back"
EOF
  printf "let's circle back tomorrow.\n" > "$TMP/dirty.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/scripts/lint_script.sh" \
    "$TMP/dirty.md" --brand test-brand
  [ "$status" -eq 1 ]
  echo "$output" | grep -q 'brand_avoid_'
}

@test "lint_script: missing brand silently uses kit defaults only" {
  printf 'a \xe2\x80\x94 b\n' > "$TMP/dirty.md"

  BRANDS_ROOT="$TMP/brands" run "$REPO_ROOT/scripts/lint_script.sh" \
    "$TMP/dirty.md" --brand nonexistent
  [ "$status" -eq 1 ]
  echo "$output" | grep -q 'em_dash'
}

@test "lint_script: multiple violations all reported" {
  printf 'a \xe2\x80\x94 b\nnot a tool, it'\''s a taste.\n' > "$TMP/dirty.md"

  run "$REPO_ROOT/scripts/lint_script.sh" "$TMP/dirty.md"
  [ "$status" -eq 1 ]
  echo "$output" | grep -q 'em_dash'
  echo "$output" | grep -q 'pattern_not_x_its_y'
}

@test "lint_script: usage error exits 2" {
  run "$REPO_ROOT/scripts/lint_script.sh"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qi 'usage'
}
