#!/usr/bin/env bash
set -euo pipefail

YES=0
PURGE_BRANDS=0
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --purge-brands) PURGE_BRANDS=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

KIT_NAME="slideshow-kit"

declare -a TARGETS=(
  "$HOME/.claude/skills/$KIT_NAME"
  "$HOME/.codex/skills/$KIT_NAME"
  "$HOME/.clawd/skills/$KIT_NAME"
)
[ -n "${OPENCLAW_HOME:-}" ] && TARGETS+=("$OPENCLAW_HOME/skills/$KIT_NAME")
[ -n "${HERMES_PLUGIN_PATH:-}" ] && TARGETS+=("$HERMES_PLUGIN_PATH/$KIT_NAME")

if [ "$YES" -ne 1 ]; then
  echo "Will remove:"
  for t in "${TARGETS[@]}"; do [ -d "$t" ] && echo "  $t"; done
  read -rp "Continue? [y/N] " ans
  [[ "$ans" == "y" || "$ans" == "Y" ]] || exit 0
fi

for t in "${TARGETS[@]}"; do
  if [ -d "$t" ]; then
    rm -rf "$t"
    echo "[PASS] removed $t"
  fi
done

if [ "$PURGE_BRANDS" -eq 1 ]; then
  # shellcheck disable=SC1091
  source "$(dirname "$0")/scripts/_resolve_brands_root.sh"
  if [ -d "$BRANDS_ROOT" ]; then
    rm -rf "$BRANDS_ROOT"
    echo "[PASS] removed brand workspaces at $BRANDS_ROOT"
  fi
else
  echo "[INFO] preserved brand workspaces (use --purge-brands to remove)"
fi
