#!/usr/bin/env bash
# migrate_brand_visual_system.sh: convert prose-shaped brand visual-system.md
# into DESIGN.md-shaped (YAML frontmatter + markdown body).
#
# Exit codes:
#   0 ok (or already migrated)
#   1 brand not found / unparseable
#   2 usage error

set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: migrate_brand_visual_system.sh --brand <slug> [--brands-root <path>] [--dry-run] [--force]

  --brand        brand slug (required)
  --brands-root  root for brand workspaces (default: $BRANDS_ROOT or ~/Documents/GitHub/slideshow-brands)
  --dry-run      print converted output to stdout, do not write
  --force        overwrite existing .bak without prompting
EOF
  exit 2
}

BRAND=""
BRANDS_ROOT="${BRANDS_ROOT:-$HOME/Documents/GitHub/slideshow-brands}"
DRY_RUN=0
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brand) BRAND="$2"; shift 2 ;;
    --brands-root) BRANDS_ROOT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    -h|--help) usage ;;
    *) echo "[ERR] unknown arg: $1" >&2; usage ;;
  esac
done

[[ -z "$BRAND" ]] && usage

VISUAL_SYSTEM="$BRANDS_ROOT/$BRAND/visual-system.md"
if [[ ! -f "$VISUAL_SYSTEM" ]]; then
  echo "[ERR] brand '$BRAND' not found at $VISUAL_SYSTEM" >&2
  exit 1
fi

# Detect shape:
#   - prose: no YAML frontmatter at all (first line is not ---)
#   - hybrid: YAML frontmatter present but no canonical visual-token keys
#   - migrated: YAML frontmatter contains palette / typography / layout / image_treatment / ui_chrome
first_line=$(head -1 "$VISUAL_SYSTEM")
if [[ "$first_line" == "---" ]]; then
  # Read the YAML frontmatter (between the first '---' and the next '---').
  frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$VISUAL_SYSTEM")
  if echo "$frontmatter" | grep -qE '^(palette|typography|layout|image_treatment|ui_chrome):'; then
    echo "[OK] already migrated: $VISUAL_SYSTEM"
    exit 0
  fi
  # Hybrid: frontmatter exists but no visual tokens. Strip frontmatter so
  # downstream extraction operates only on the prose body, then re-emit
  # frontmatter with both the existing keys and the extracted visual tokens.
  echo "[INFO] hybrid shape detected: visual tokens are still in the markdown body" >&2
  HYBRID=1
  # Capture the existing frontmatter for re-injection.
  EXISTING_FRONTMATTER="$frontmatter"
  # The body starts after the second `---` line.
  BODY_START_LINE=$(awk '/^---$/{count++; if (count==2) {print NR+1; exit}}' "$VISUAL_SYSTEM")
  BODY=$(tail -n "+$BODY_START_LINE" "$VISUAL_SYSTEM")
else
  HYBRID=0
  EXISTING_FRONTMATTER=""
  BODY=$(cat "$VISUAL_SYSTEM")
fi

# For extraction, redirect grep/awk against a temp file containing only the body.
EXTRACT_FILE=$(mktemp)
trap 'rm -f "$EXTRACT_FILE"' EXIT
printf '%s' "$BODY" > "$EXTRACT_FILE"

# Extract tokens.
extract_hex() {
  # $1 = label, $2 = file. Outputs first matching hex on a line containing $1.
  grep -i "$1" "$2" | grep -oE '#[0-9A-Fa-f]{6}' | head -1 || true
}

extract_field() {
  # $1 = label, $2 = file. Tries:
  #   - "**Label:** value"
  #   - "Label: value" (with optional leading bullet)
  #   - "- Label: value"
  local val
  val=$(grep -iE "^[-*]?[[:space:]]*\*\*$1\*\*[: ]" "$2" 2>/dev/null | head -1 | sed -E 's/^[-*]?[[:space:]]*\*\*[^:]+\*\*:?[[:space:]]*//' | tr -d '"') || true
  if [ -z "$val" ]; then
    val=$(grep -iE "^[-*]?[[:space:]]*$1[[:space:]]*:" "$2" 2>/dev/null | head -1 | sed -E 's/^[-*]?[[:space:]]*[^:]+:[[:space:]]*//' | tr -d '"') || true
  fi
  printf '%s' "$val"
}

extract_freeform() {
  # $1 = section heading. Output the first non-blank, non-bullet line under heading.
  awk -v section="$1" '
    BEGIN { found=0 }
    $0 ~ "^# *" section "$" || $0 ~ "^## *" section "$" { found=1; next }
    found && /^#+ / { exit }
    found && NF > 0 && $1 != "-" { print; exit }
  ' "$2"
}

bg=$(extract_hex "Background" "$EXTRACT_FILE")
accent=$(extract_hex "accent" "$EXTRACT_FILE")
text_color=$(extract_hex "Text" "$EXTRACT_FILE")
heading_family=$(extract_field "Heading family" "$EXTRACT_FILE")
heading_weight=$(extract_field "Headline weight" "$EXTRACT_FILE")
[[ -z "$heading_weight" ]] && heading_weight=$(extract_field "Heading weight" "$EXTRACT_FILE")
body_family=$(extract_field "Body family" "$EXTRACT_FILE")
body_weight=$(extract_field "Body weight" "$EXTRACT_FILE")
density=$(extract_field "Density" "$EXTRACT_FILE")
hero_position=$(extract_field "Hero position" "$EXTRACT_FILE")
image_treatment=$(extract_freeform "Image treatment" "$EXTRACT_FILE")
pill_tags=$(extract_field "Pill tags" "$EXTRACT_FILE")

# If we got nothing, it's unparseable.
if [[ -z "$bg$accent$text_color$heading_family$heading_weight$body_family$density$hero_position" ]]; then
  echo "[ERR] no recognizable tokens in $VISUAL_SYSTEM" >&2
  echo "[hint] expected sections: # Palette, # Typography, # Layout, # Image treatment, # UI chrome (single or double #)" >&2
  exit 1
fi

# Compose YAML frontmatter.
yaml=$'---\n'
# Re-inject existing non-visual-token keys first (e.g. brand, last-updated).
if [ -n "$EXISTING_FRONTMATTER" ]; then
  while IFS= read -r yline; do
    [ -z "$yline" ] && continue
    yaml+="$yline"$'\n'
  done <<< "$EXISTING_FRONTMATTER"
fi
# Then visual tokens.
if [[ -n "$bg$accent$text_color" ]]; then
  yaml+=$'palette:\n'
  [[ -n "$bg" ]] && yaml+="  background: \"$bg\""$'\n'
  [[ -n "$accent" ]] && yaml+="  primary_accent: \"$accent\""$'\n'
  [[ -n "$text_color" ]] && yaml+="  text: \"$text_color\""$'\n'
fi
if [[ -n "$heading_family$heading_weight$body_family$body_weight" ]]; then
  yaml+=$'typography:\n'
  [[ -n "$heading_family" ]] && yaml+="  heading_family: \"$heading_family\""$'\n'
  [[ -n "$heading_weight" ]] && yaml+="  heading_weight: \"$heading_weight\""$'\n'
  [[ -n "$body_family" ]] && yaml+="  body_family: \"$body_family\""$'\n'
  [[ -n "$body_weight" ]] && yaml+="  body_weight: \"$body_weight\""$'\n'
fi
if [[ -n "$density$hero_position" ]]; then
  yaml+=$'layout:\n'
  [[ -n "$density" ]] && yaml+="  density: \"$density\""$'\n'
  [[ -n "$hero_position" ]] && yaml+="  hero_position: \"$hero_position\""$'\n'
fi
if [[ -n "$image_treatment" ]]; then
  yaml+="image_treatment: \"$image_treatment\""$'\n'
fi
if [[ -n "$pill_tags" ]]; then
  yaml+=$'ui_chrome:\n'
  yaml+="  pill_tags: $pill_tags"$'\n'
fi
yaml+=$'---\n\n'

if [ "$HYBRID" -eq 1 ]; then
  output="${yaml}${BODY}"
else
  output="${yaml}${BODY}"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "$output"
  exit 0
fi

# Write backup unless one exists and --force not given.
backup="$VISUAL_SYSTEM.bak"
if [[ -f "$backup" && "$FORCE" -eq 0 ]]; then
  echo "[ERR] backup already exists: $backup (rerun with --force to overwrite)" >&2
  exit 1
fi
cp "$VISUAL_SYSTEM" "$backup"

printf '%s' "$output" > "$VISUAL_SYSTEM"

echo "[OK] migrated: $VISUAL_SYSTEM (backup: $backup)"
