#!/usr/bin/env bash
set -euo pipefail

NO_POSTIZ_AUTH=0
NO_DEPS_CHECK=0
for arg in "$@"; do
  case "$arg" in
    --no-postiz-auth) NO_POSTIZ_AUTH=1 ;;
    --no-deps-check) NO_DEPS_CHECK=1 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIT_NAME="slideshow-kit"

# 1. Check deps unless skipped
if [ "$NO_DEPS_CHECK" -eq 0 ]; then
  for cmd in git python3 jq curl; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "[FAIL] missing required command: $cmd" >&2
      exit 1
    fi
  done
fi

# 2. Detect agent skill paths
declare -a TARGETS=()
[ -d "$HOME/.claude/skills" ] && TARGETS+=("$HOME/.claude/skills/$KIT_NAME")
[ -d "$HOME/.codex/skills" ] && TARGETS+=("$HOME/.codex/skills/$KIT_NAME")
if [ -n "${OPENCLAW_HOME:-}" ] && [ -d "$OPENCLAW_HOME/skills" ]; then
  TARGETS+=("$OPENCLAW_HOME/skills/$KIT_NAME")
elif [ -d "$HOME/.clawd/skills" ]; then
  TARGETS+=("$HOME/.clawd/skills/$KIT_NAME")
fi
[ -n "${HERMES_PLUGIN_PATH:-}" ] && [ -d "$HERMES_PLUGIN_PATH" ] && TARGETS+=("$HERMES_PLUGIN_PATH/$KIT_NAME")

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "[FAIL] no supported agent paths detected" >&2
  echo "Looked for: ~/.claude/skills, ~/.codex/skills, OpenClaw, Hermes" >&2
  exit 1
fi

# 3. Install to each target (rsync for atomic copy)
for target in "${TARGETS[@]}"; do
  rm -rf "$target"
  mkdir -p "$(dirname "$target")"
  rsync -a --exclude='.git' --exclude='runs/' --exclude='output/' \
    --exclude='__pycache__' --exclude='.pytest_cache' \
    "$KIT_DIR/" "$target/"
  echo "[PASS] installed to $target"
done

# 4. Install postiz CLI if missing
if ! command -v postiz >/dev/null 2>&1; then
  echo "[INFO] installing postiz CLI"
  npm install -g postiz
fi

# 5. Run postiz auth unless skipped
if [ "$NO_POSTIZ_AUTH" -eq 0 ]; then
  echo "[INFO] running postiz auth (interactive)"
  postiz login || echo "[WARN] postiz login skipped or failed"
fi

# 6. Scaffold global config
GLOBAL_CONFIG_DIR="$HOME/.clawd/slideshow-kit"
GLOBAL_CONFIG="$GLOBAL_CONFIG_DIR/config.json"
mkdir -p "$GLOBAL_CONFIG_DIR"
if [ ! -f "$GLOBAL_CONFIG" ]; then
  cat > "$GLOBAL_CONFIG" <<'JSON'
{
  "brands_root": null,
  "default_brand": null,
  "kit_version": "0.1.0"
}
JSON
  echo "[PASS] scaffolded $GLOBAL_CONFIG"
fi

# 7. Print next steps
cat <<'NEXT'

[PASS] Slideshow Kit installed.

Next steps:
  1. Scaffold a brand:   ./scripts/init_brand.sh <slug>
  2. Edit brand DNA:     $EDITOR ./brands/<slug>/{brand-voice,brand-perspective,visual-system}.md
  3. Health check:       ./doctor.sh

Brand state lives at ./brands/<slug>/ by default (gitignored).
To centralize: export SLIDESHOW_BRANDS_ROOT=/path/to/brands

Optional:
  - Telegram check-in: see references/telegram-setup.md
NEXT
