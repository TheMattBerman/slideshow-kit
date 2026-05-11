#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  TMP="$BATS_TMPDIR/migrate-$$"
  mkdir -p "$TMP/brands/test-brand"
}

teardown() {
  rm -rf "$TMP"
}

@test "migrate: prose input becomes DESIGN.md-shaped output" {
  cp "$REPO_ROOT/tests/fixtures/visual_system/prose_input.md" \
     "$TMP/brands/test-brand/visual-system.md"

  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand test-brand --brands-root "$TMP/brands"

  [ "$status" -eq 0 ]
  head -1 "$TMP/brands/test-brand/visual-system.md" | grep -q '^---$'
  grep -q 'background: "#0D1117"' "$TMP/brands/test-brand/visual-system.md"
  grep -q 'primary_accent: "#F43F5E"' "$TMP/brands/test-brand/visual-system.md"
  grep -q 'heading_family: "Inter"' "$TMP/brands/test-brand/visual-system.md"
  [ -f "$TMP/brands/test-brand/visual-system.md.bak" ]
}

@test "migrate: already-yaml input is no-op" {
  cp "$REPO_ROOT/tests/fixtures/visual_system/already_yaml.md" \
     "$TMP/brands/test-brand/visual-system.md"

  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand test-brand --brands-root "$TMP/brands"

  [ "$status" -eq 0 ]
  echo "$output" | grep -q '\[OK\] already migrated'
  [ ! -f "$TMP/brands/test-brand/visual-system.md.bak" ]
}

@test "migrate: --dry-run prints diff without writing" {
  cp "$REPO_ROOT/tests/fixtures/visual_system/prose_input.md" \
     "$TMP/brands/test-brand/visual-system.md"
  original_md5=$(md5 -q "$TMP/brands/test-brand/visual-system.md" 2>/dev/null \
                 || md5sum "$TMP/brands/test-brand/visual-system.md" | cut -d' ' -f1)

  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand test-brand --brands-root "$TMP/brands" --dry-run

  [ "$status" -eq 0 ]
  echo "$output" | grep -q '^---$'
  echo "$output" | grep -q 'palette:'

  new_md5=$(md5 -q "$TMP/brands/test-brand/visual-system.md" 2>/dev/null \
            || md5sum "$TMP/brands/test-brand/visual-system.md" | cut -d' ' -f1)
  [ "$original_md5" = "$new_md5" ]
}

@test "migrate: missing brand exits non-zero" {
  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand nonexistent --brands-root "$TMP/brands"

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'not found'
}

@test "migrate: usage error on missing --brand" {
  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh"
  [ "$status" -eq 2 ]
  echo "$output" | grep -qi 'usage'
}

@test "migrate: --force overwrites existing .bak" {
  cp "$REPO_ROOT/tests/fixtures/visual_system/prose_input.md" \
     "$TMP/brands/test-brand/visual-system.md"
  echo "old backup" > "$TMP/brands/test-brand/visual-system.md.bak"

  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand test-brand --brands-root "$TMP/brands" --force

  [ "$status" -eq 0 ]
  ! grep -q "old backup" "$TMP/brands/test-brand/visual-system.md.bak"
}

@test "migrate: idempotent on second run" {
  cp "$REPO_ROOT/tests/fixtures/visual_system/prose_input.md" \
     "$TMP/brands/test-brand/visual-system.md"

  "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
    --brand test-brand --brands-root "$TMP/brands"
  first_md5=$(md5 -q "$TMP/brands/test-brand/visual-system.md" 2>/dev/null \
              || md5sum "$TMP/brands/test-brand/visual-system.md" | cut -d' ' -f1)

  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand test-brand --brands-root "$TMP/brands"

  [ "$status" -eq 0 ]
  echo "$output" | grep -q '\[OK\] already migrated'
  second_md5=$(md5 -q "$TMP/brands/test-brand/visual-system.md" 2>/dev/null \
               || md5sum "$TMP/brands/test-brand/visual-system.md" | cut -d' ' -f1)
  [ "$first_md5" = "$second_md5" ]
}

@test "migrate: backup file matches original content" {
  cp "$REPO_ROOT/tests/fixtures/visual_system/prose_input.md" \
     "$TMP/brands/test-brand/visual-system.md"
  original=$(cat "$TMP/brands/test-brand/visual-system.md")

  "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
    --brand test-brand --brands-root "$TMP/brands" >/dev/null

  backup=$(cat "$TMP/brands/test-brand/visual-system.md.bak")
  [ "$original" = "$backup" ]
}

@test "migrate: hybrid frontmatter (no visual tokens) is migrated" {
  cat > "$TMP/brands/test-brand/visual-system.md" <<'EOF'
---
brand: test-brand
last-updated: 2026-05-04
---

# Palette

- Background: `#0D1117`
- Primary accent: `#F43F5E`

# Typography

- Headline weight: extra-bold
- Body weight: regular
EOF

  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand test-brand --brands-root "$TMP/brands"

  [ "$status" -eq 0 ]
  # Existing keys are preserved.
  grep -q '^brand: test-brand' "$TMP/brands/test-brand/visual-system.md"
  # New visual-token keys are added.
  grep -q 'background: "#0D1117"' "$TMP/brands/test-brand/visual-system.md"
  grep -q 'primary_accent: "#F43F5E"' "$TMP/brands/test-brand/visual-system.md"
  grep -q 'heading_weight: "extra-bold"' "$TMP/brands/test-brand/visual-system.md"
  [ -f "$TMP/brands/test-brand/visual-system.md.bak" ]
}

@test "migrate: fully-migrated frontmatter (with palette key) is no-op" {
  cat > "$TMP/brands/test-brand/visual-system.md" <<'EOF'
---
brand: test-brand
palette:
  background: "#FFFFFF"
typography:
  heading_family: "Inter"
---

# body
EOF

  run "$REPO_ROOT/scripts/migrate_brand_visual_system.sh" \
      --brand test-brand --brands-root "$TMP/brands"

  [ "$status" -eq 0 ]
  echo "$output" | grep -q '\[OK\] already migrated'
  [ ! -f "$TMP/brands/test-brand/visual-system.md.bak" ]
}
