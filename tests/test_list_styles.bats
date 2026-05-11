#!/usr/bin/env bats

setup() {
  KIT_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  cd "$KIT_DIR"
  TMP="$(mktemp -d)"
  export SLIDESHOW_BRANDS_ROOT="$TMP/brands"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/acme/styles"
  cp -r "$KIT_DIR/references/styles/social_native" \
        "$SLIDESHOW_BRANDS_ROOT/acme/styles/social_native"
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/config.json" <<'JSON'
{
  "brand": "acme",
  "default_style": "social_native"
}
JSON
}

teardown() {
  rm -rf "$TMP"
}

@test "list_styles.sh exits 2 on missing brand arg" {
  run ./scripts/list_styles.sh
  [ "$status" -eq 2 ]
}

@test "list_styles.sh exits 1 on unknown brand" {
  run ./scripts/list_styles.sh nonexistent
  [ "$status" -eq 1 ]
}

@test "list_styles.sh prints default_style and style names" {
  run ./scripts/list_styles.sh acme
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "default_style: social_native"
  echo "$output" | grep -q "social_native"
}

@test "list_styles.sh reports <unset> when default_style absent" {
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/config.json" <<'JSON'
{
  "brand": "acme"
}
JSON
  run ./scripts/list_styles.sh acme
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "default_style: <unset>"
}

@test "list_styles.sh reports empty dir hint when styles missing" {
  rm -rf "$SLIDESHOW_BRANDS_ROOT/acme/styles"
  run ./scripts/list_styles.sh acme
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "no styles dir"
}
