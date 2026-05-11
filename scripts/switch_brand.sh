#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <slug>" >&2
  exit 2
fi

SLUG="$1"
# shellcheck disable=SC1091
source "$(dirname "$0")/_resolve_brands_root.sh"
GLOBAL_CONFIG_DIR="$HOME/.clawd/slideshow-kit"
GLOBAL_CONFIG="$GLOBAL_CONFIG_DIR/config.json"

if [ ! -d "$BRANDS_ROOT/$SLUG" ]; then
  echo "[FAIL] brand workspace not found: $BRANDS_ROOT/$SLUG" >&2
  echo "       create with: ./scripts/init_brand.sh $SLUG" >&2
  exit 1
fi

mkdir -p "$GLOBAL_CONFIG_DIR"
if [ ! -f "$GLOBAL_CONFIG" ]; then
  cat > "$GLOBAL_CONFIG" <<JSON
{
  "brands_root": null,
  "default_brand": "$SLUG",
  "kit_version": "0.1.0"
}
JSON
else
  tmp="$(mktemp)"
  jq --arg s "$SLUG" '.default_brand = $s' "$GLOBAL_CONFIG" > "$tmp"
  mv "$tmp" "$GLOBAL_CONFIG"
fi

echo "[PASS] default brand set to $SLUG"
