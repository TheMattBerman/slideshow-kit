#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC1091
source "$(dirname "$0")/_resolve_brands_root.sh"
GLOBAL_CONFIG="$HOME/.clawd/slideshow-kit/config.json"

if [ ! -d "$BRANDS_ROOT" ]; then
  echo "[INFO] no brands found at $BRANDS_ROOT"
  echo "       run: ./scripts/init_brand.sh <slug>"
  exit 0
fi

DEFAULT=""
if [ -f "$GLOBAL_CONFIG" ]; then
  DEFAULT="$(jq -r '.default_brand // empty' "$GLOBAL_CONFIG" 2>/dev/null || true)"
fi

found=0
for d in "$BRANDS_ROOT"/*/; do
  [ -d "$d" ] || continue
  slug="$(basename "$d")"
  found=1
  if [ "$slug" = "$DEFAULT" ]; then
    echo "$slug (default)"
  else
    echo "$slug"
  fi
done

if [ "$found" -eq 0 ]; then
  echo "[INFO] no brands found"
fi
