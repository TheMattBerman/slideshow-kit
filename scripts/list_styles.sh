#!/usr/bin/env bash
# list_styles.sh: enumerate the styles available for a brand.
# Reports the brand's default_style and counts refs per style.
#
# Exit codes:
#   0 ok
#   1 brand not found
#   2 usage error

set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <brand-slug>" >&2
  exit 2
fi

BRAND="$1"
KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$(dirname "$0")/_resolve_brands_root.sh"
BRAND_DIR="$BRANDS_ROOT/$BRAND"

if [ ! -d "$BRAND_DIR" ]; then
  echo "[FAIL] brand workspace not found: $BRAND_DIR" >&2
  exit 1
fi

CONFIG="$BRAND_DIR/config.json"
DEFAULT_STYLE=""
if [ -f "$CONFIG" ]; then
  DEFAULT_STYLE="$(jq -r '.default_style // empty' "$CONFIG" 2>/dev/null || true)"
fi

STYLES_DIR="$BRAND_DIR/styles"
echo "$BRAND"
echo "  default_style: ${DEFAULT_STYLE:-<unset>}"
echo "  styles:"

if [ ! -d "$STYLES_DIR" ]; then
  echo "    (no styles dir; run scripts/add_style.sh to create one)"
  exit 0
fi

found=0
for style_dir in "$STYLES_DIR"/*/; do
  [ -d "$style_dir" ] || continue
  found=1
  style_name="$(basename "$style_dir")"
  refs_count=0
  if [ -d "$style_dir/refs" ]; then
    refs_count=$(find "$style_dir/refs" \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" \) -type f 2>/dev/null | wc -l | tr -d ' ')
  fi
  marker=""
  if [ "$style_name" = "$DEFAULT_STYLE" ]; then
    marker=" (default)"
  fi
  printf "    - %-30s (%d refs)%s\n" "$style_name" "$refs_count" "$marker"
done

if [ "$found" -eq 0 ]; then
  echo "    (empty styles dir; run scripts/add_style.sh)"
fi
