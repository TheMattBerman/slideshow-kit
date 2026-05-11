#!/usr/bin/env bats

setup() {
  KIT_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  cd "$KIT_DIR"
  TMP="$(mktemp -d)"
  export SLIDESHOW_BRANDS_ROOT="$TMP/brands"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/acme"
  echo '{"brand":"acme"}' > "$SLIDESHOW_BRANDS_ROOT/acme/config.json"
}

teardown() {
  rm -rf "$TMP"
}

@test "add_style.sh exits 2 on missing flags" {
  run ./scripts/add_style.sh
  [ "$status" -eq 2 ]
}

@test "add_style.sh exits 2 on missing --description and --refs" {
  run ./scripts/add_style.sh --brand acme --style demo
  [ "$status" -eq 2 ]
}

@test "add_style.sh exits 2 on invalid style name (not snake_case)" {
  run ./scripts/add_style.sh --brand acme --style "Bad-Name" --description "x"
  [ "$status" -eq 2 ]
}

@test "add_style.sh exits 1 on unknown brand" {
  run ./scripts/add_style.sh --brand nonexistent --style demo --description "x"
  [ "$status" -eq 1 ]
}

@test "add_style.sh creates style dir and stub DESIGN.md from description only" {
  run ./scripts/add_style.sh --brand acme --style my_style --description "dark editorial"
  [ "$status" -eq 0 ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/acme/styles/my_style/DESIGN.md" ]
  grep -q "name: my_style" "$SLIDESHOW_BRANDS_ROOT/acme/styles/my_style/DESIGN.md"
  grep -q "dark editorial" "$SLIDESHOW_BRANDS_ROOT/acme/styles/my_style/DESIGN.md"
}

@test "add_style.sh copies provided refs into refs/" {
  echo "fake png 1" > "$TMP/r1.png"
  echo "fake png 2" > "$TMP/r2.png"
  run ./scripts/add_style.sh --brand acme --style my_style \
    --refs "$TMP/r1.png,$TMP/r2.png"
  [ "$status" -eq 0 ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/acme/styles/my_style/refs/r1.png" ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/acme/styles/my_style/refs/r2.png" ]
}

@test "add_style.sh exits 3 when style exists without --force" {
  ./scripts/add_style.sh --brand acme --style my_style --description "first"
  run ./scripts/add_style.sh --brand acme --style my_style --description "second"
  [ "$status" -eq 3 ]
}

@test "add_style.sh overwrites with --force" {
  ./scripts/add_style.sh --brand acme --style my_style --description "first"
  run ./scripts/add_style.sh --brand acme --style my_style --description "second" --force
  [ "$status" -eq 0 ]
  grep -q "second" "$SLIDESHOW_BRANDS_ROOT/acme/styles/my_style/DESIGN.md"
}
