#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: $0 <slug> [--force]" >&2
  exit 2
fi

SLUG="$1"
FORCE=0
shift
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# Validate slug
if ! [[ "$SLUG" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  echo "[FAIL] slug must be lowercase alnum + hyphens, starting alnum" >&2
  exit 1
fi

KIT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TEMPLATES="$KIT_DIR/references/brand-templates"
# shellcheck disable=SC1091
source "$(dirname "$0")/_resolve_brands_root.sh"
BRAND_DIR="$BRANDS_ROOT/$SLUG"
TODAY="$(date +%Y-%m-%d)"

if [ -d "$BRAND_DIR" ] && [ "$FORCE" -ne 1 ]; then
  echo "[FAIL] brand workspace already exists: $BRAND_DIR (use --force to overwrite)" >&2
  exit 1
fi

mkdir -p "$BRAND_DIR"

for f in brand-voice.md brand-perspective.md visual-system.md; do
  src="$TEMPLATES/$f"
  dst="$BRAND_DIR/$f"
  if [ ! -f "$src" ]; then
    echo "[FAIL] template not found: $src" >&2
    exit 1
  fi
  sed -e "s/<slug>/$SLUG/g" -e "s/<YYYY-MM-DD>/$TODAY/g" "$src" > "$dst"
done

cat > "$BRAND_DIR/config.json" <<JSON
{
  "brand": "$SLUG",
  "mode": "draft",
  "lookback_days": 7,
  "posts_per_day": 1,
  "default_style": "social_native",
  "styles_per_day": ["social_native"],
  "checkin": {
    "channel": "agent",
    "timeout_minutes": 30,
    "telegram_chat_id": null
  },
  "postiz": {
    "integration_ids": []
  },
  "created_on": "$TODAY",
  "runs_history": 0
}
JSON

mkdir -p "$BRAND_DIR/runs"

# v0.6.0: copy the kit's social_native reference style as a starting selectable.
# Operators may run scripts/add_style.sh later to add more styles.
mkdir -p "$BRAND_DIR/styles"
cp -r "$KIT_DIR/references/styles/social_native" "$BRAND_DIR/styles/"

# Set default_style + styles_per_day in the brand's config.json. If config
# already exists (re-run after init_brand), preserve it but ensure both
# fields are present.
CONFIG_PATH="$BRAND_DIR/config.json"
if [ -f "$CONFIG_PATH" ]; then
  needs_patch=0
  grep -q '"default_style"' "$CONFIG_PATH" || needs_patch=1
  grep -q '"styles_per_day"' "$CONFIG_PATH" || needs_patch=1
  if [ "$needs_patch" -eq 1 ]; then
    # Insert missing fields via jq for correctness.
    tmp=$(mktemp)
    jq 'if .default_style == null then . + {default_style: "social_native"} else . end
        | if .styles_per_day == null then . + {styles_per_day: ["social_native"]} else . end' \
      "$CONFIG_PATH" > "$tmp" && mv "$tmp" "$CONFIG_PATH"
  fi
else
  cat > "$CONFIG_PATH" <<JSON
{
  "brand": "$SLUG",
  "default_style": "social_native",
  "styles_per_day": ["social_native"]
}
JSON
fi

echo "[PASS] brand workspace ready at $BRAND_DIR"
echo "[INFO] edit the three DNA files, then run: ./doctor.sh"
