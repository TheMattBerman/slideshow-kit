#!/usr/bin/env bash
set -euo pipefail

# generate_golden_example.sh
#
# Publish a golden run from $BRANDS_ROOT/<brand>/runs/<date> into
# examples/<brand>-day-1-output/ for shipping with the kit.
#
# Usage:
#   scripts/generate_golden_example.sh [BRAND] [SOURCE_DATE]
#
# Defaults: BRAND=matt, SOURCE_DATE=today

BRAND="${1:-matt}"
SOURCE_DATE="${2:-$(date +%Y-%m-%d)}"

KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$(dirname "$0")/_resolve_brands_root.sh"

SRC="$BRANDS_ROOT/$BRAND/runs/$SOURCE_DATE"
DEST="$KIT_DIR/examples/$BRAND-day-1-output"

if [ ! -d "$SRC" ]; then
  echo "[FAIL] source run dir not found: $SRC" >&2
  echo "       check BRAND ($BRAND) and SOURCE_DATE ($SOURCE_DATE), or run the kit first." >&2
  exit 1
fi

if [ -e "$DEST" ]; then
  echo "[FAIL] destination already exists: $DEST" >&2
  echo "       remove it first if you want to regenerate." >&2
  exit 1
fi

mkdir -p "$DEST"

branded_count=0
socialnative_count=0

for sub in branded social-native; do
  if [ -d "$SRC/$sub" ]; then
    mkdir -p "$DEST/$sub"
    # silence no-match: count check below is the source of truth
    cp "$SRC/$sub"/*.png "$DEST/$sub/" 2>/dev/null || true
    count=$(find "$DEST/$sub" -maxdepth 1 -name '*.png' -type f | wc -l | tr -d ' ')
    if [ "$sub" = "branded" ]; then
      branded_count="$count"
    else
      socialnative_count="$count"
    fi
  fi
done

if [ "$branded_count" -eq 0 ] && [ "$socialnative_count" -eq 0 ]; then
  echo "[FAIL] no PNGs found in either format subdir of $SRC" >&2
  exit 1
fi

echo "[PASS] golden example written to $DEST (branded: ${branded_count} PNGs, social-native: ${socialnative_count} PNGs)"
echo "[INFO] review and commit:"
echo "  git add examples/$BRAND-day-1-output"
echo "  git commit -m \"docs(examples): add $BRAND day-1 golden run output\""
