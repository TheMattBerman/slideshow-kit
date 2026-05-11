#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  export SLIDESHOW_BRANDS_ROOT="$TEST_HOME/brands"
  cd "$BATS_TEST_DIRNAME/.."
  ./scripts/init_brand.sh acme
  ./scripts/init_brand.sh beta
}
teardown() { rm -rf "$TEST_HOME"; }

@test "list_brands.sh lists all brand workspaces" {
  run ./scripts/list_brands.sh
  [ "$status" -eq 0 ]
  [[ "$output" =~ "acme" ]]
  [[ "$output" =~ "beta" ]]
}

@test "list_brands.sh marks default brand" {
  ./scripts/switch_brand.sh acme
  run ./scripts/list_brands.sh
  [[ "$output" =~ "acme (default)" ]] || [[ "$output" =~ acme.*default ]]
}

@test "switch_brand.sh sets default in global config" {
  run ./scripts/switch_brand.sh beta
  [ "$status" -eq 0 ]
  grep -q '"default_brand": "beta"' "$HOME/.clawd/slideshow-kit/config.json"
}

@test "switch_brand.sh fails on non-existent brand" {
  run ./scripts/switch_brand.sh nonexistent
  [ "$status" -eq 1 ]
}
