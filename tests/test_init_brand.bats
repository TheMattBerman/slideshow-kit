#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  export SLIDESHOW_BRANDS_ROOT="$TEST_HOME/brands"
  cd "$BATS_TEST_DIRNAME/.."
}
teardown() { rm -rf "$TEST_HOME"; }

@test "init_brand.sh creates workspace with three template files" {
  run ./scripts/init_brand.sh testbrand
  [ "$status" -eq 0 ]
  [ -d "$SLIDESHOW_BRANDS_ROOT/testbrand" ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/testbrand/brand-voice.md" ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/testbrand/brand-perspective.md" ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/testbrand/visual-system.md" ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/testbrand/config.json" ]
}

@test "init_brand.sh fails on duplicate brand without --force" {
  ./scripts/init_brand.sh testbrand
  run ./scripts/init_brand.sh testbrand
  [ "$status" -eq 1 ]
  [[ "$output" =~ "already exists" ]]
}

@test "init_brand.sh --force overwrites existing brand" {
  ./scripts/init_brand.sh testbrand
  echo "custom" > "$SLIDESHOW_BRANDS_ROOT/testbrand/brand-voice.md"
  run ./scripts/init_brand.sh testbrand --force
  [ "$status" -eq 0 ]
  ! grep -q "^custom$" "$SLIDESHOW_BRANDS_ROOT/testbrand/brand-voice.md"
}

@test "init_brand.sh substitutes <slug> in templates" {
  ./scripts/init_brand.sh acme
  grep -q "brand: acme" "$SLIDESHOW_BRANDS_ROOT/acme/brand-voice.md"
  grep -q "brand: acme" "$SLIDESHOW_BRANDS_ROOT/acme/brand-perspective.md"
  grep -q "brand: acme" "$SLIDESHOW_BRANDS_ROOT/acme/visual-system.md"
}

@test "init_brand.sh copies social_native style into new brand" {
  run ./scripts/init_brand.sh styleddemo
  [ "$status" -eq 0 ]
  [ -d "$SLIDESHOW_BRANDS_ROOT/styleddemo/styles/social_native" ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/styleddemo/styles/social_native/DESIGN.md" ]
}

@test "init_brand.sh writes default_style: social_native to config.json" {
  run ./scripts/init_brand.sh styleddemo
  [ "$status" -eq 0 ]
  grep -q '"default_style": "social_native"' "$SLIDESHOW_BRANDS_ROOT/styleddemo/config.json" \
    || grep -q '"default_style":"social_native"' "$SLIDESHOW_BRANDS_ROOT/styleddemo/config.json"
}

@test "init_brand.sh --force preserves social_native after re-init" {
  ./scripts/init_brand.sh styleddemo
  run ./scripts/init_brand.sh styleddemo --force
  [ "$status" -eq 0 ]
  grep -q "social_native" "$SLIDESHOW_BRANDS_ROOT/styleddemo/config.json"
  [ -d "$SLIDESHOW_BRANDS_ROOT/styleddemo/styles/social_native" ]
}
