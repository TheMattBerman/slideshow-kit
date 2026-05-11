#!/usr/bin/env bash
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

EXIT=0

check() {
  local level="$1"; local msg="$2"
  echo "[$level] $msg"
  [ "$level" = "FAIL" ] && EXIT=1
}

KIT_NAME="slideshow-kit"

# 1. Agent installs
declare -a INSTALLED=()
for path in "$HOME/.claude/skills/$KIT_NAME" \
            "$HOME/.codex/skills/$KIT_NAME" \
            "$HOME/.clawd/skills/$KIT_NAME"; do
  [ -d "$path" ] && INSTALLED+=("$path")
done
[ -n "${OPENCLAW_HOME:-}" ] && [ -d "$OPENCLAW_HOME/skills/$KIT_NAME" ] && INSTALLED+=("$OPENCLAW_HOME/skills/$KIT_NAME")
[ -n "${HERMES_PLUGIN_PATH:-}" ] && [ -d "$HERMES_PLUGIN_PATH/$KIT_NAME" ] && INSTALLED+=("$HERMES_PLUGIN_PATH/$KIT_NAME")

if [ "${#INSTALLED[@]}" -eq 0 ]; then
  check FAIL "no agent installs detected: run install.sh"
else
  for p in "${INSTALLED[@]}"; do check PASS "installed: $p"; done
fi

# 2. gpt-image-2 key
if [ -n "${OPENAI_API_KEY:-}" ]; then
  check PASS "OPENAI_API_KEY present"
else
  check WARN "OPENAI_API_KEY missing: image generation will fail"
fi

# 3. postiz CLI
if command -v postiz >/dev/null 2>&1; then
  check PASS "postiz CLI installed"
else
  check WARN "postiz CLI missing - install with: npm i -g postiz"
fi

# 3a. POSTIZ_API_URL sanity check (self-hosted gotcha)
if [ -n "${POSTIZ_API_URL:-}" ]; then
  if printf '%s' "$POSTIZ_API_URL" | grep -qE '/api/?$'; then
    check PASS "POSTIZ_API_URL set with /api suffix: $POSTIZ_API_URL"
  else
    check WARN "POSTIZ_API_URL is set but does not end in /api. Self-hosted postiz CLI requires the /api suffix; without it the CLI hits the auth UI and gets HTML back. Set POSTIZ_API_URL=<host>/api."
  fi
fi

# 4. Telegram (optional)
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  check PASS "TELEGRAM_BOT_TOKEN present"
else
  check WARN "TELEGRAM_BOT_TOKEN missing: Telegram check-in disabled (see references/telegram-setup.md)"
fi

# 5. ImageMagick (required for --mode anchor-chain in social-native-carousel)
if command -v magick >/dev/null 2>&1 || command -v convert >/dev/null 2>&1; then
  bin="$(command -v magick || command -v convert)"
  check PASS "ImageMagick: $bin"
else
  check WARN "ImageMagick not found"
  echo "       Required for --mode anchor-chain (the default for social-native-carousel)"
  echo "       Install: brew install imagemagick"
fi

# 6. Per-brand health
# shellcheck disable=SC1091
source "$(dirname "$0")/scripts/_resolve_brands_root.sh"
if [ -d "$BRANDS_ROOT" ]; then
  for brand_dir in "$BRANDS_ROOT"/*/; do
    [ -d "$brand_dir" ] || continue
    slug="$(basename "$brand_dir")"
    missing=()
    for f in brand-voice.md brand-perspective.md visual-system.md; do
      [ -f "$brand_dir/$f" ] || missing+=("$f")
    done
    if [ "${#missing[@]}" -eq 0 ]; then
      check PASS "brand[$slug]: all DNA files present"
    else
      check FAIL "brand[$slug]: missing ${missing[*]}"
    fi

    # Autopilot live-spend gate (per references/live-spend-gating.md)
    cfg="$brand_dir/config.json"
    if [ -f "$cfg" ]; then
      bmode="$(grep -o '"mode":[^,}]*' "$cfg" | head -n1 | sed 's/.*"mode"://; s/[" ]//g')"
      bruns="$(grep -o '"runs_history":[0-9]*' "$cfg" | head -n1 | sed 's/.*"runs_history"://')"
      if [ "${bmode:-}" = "autopilot" ] && [ "${bruns:-0}" -lt 7 ]; then
        check WARN "brand[$slug]: autopilot mode with only ${bruns:-0} runs of history (required: 7); see references/live-spend-gating.md"
      fi
    fi

    # v0.6.0: warn if any brand has an empty or missing styles dir.
    styles_dir="$brand_dir/styles"
    if [ ! -d "$styles_dir" ]; then
      echo "[WARN] brand $slug has no styles/ dir; run scripts/init_brand.sh --force or scripts/add_style.sh" >&2
    else
      style_count=$(find "$styles_dir" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')
      if [ "$style_count" -eq 0 ]; then
        echo "[WARN] brand $slug has empty styles/ dir; run scripts/add_style.sh" >&2
      fi
    fi

    # v0.6.1: warn if brand visual-system.md is prose-shaped or hybrid-shaped (Bug 19 guard).
    visual_system="$brand_dir/visual-system.md"
    if [ -f "$visual_system" ]; then
      first=$(head -n1 "$visual_system")
      needs_migration=0
      if [ "$first" != "---" ]; then
        needs_migration=1
      else
        # Hybrid: frontmatter exists but no canonical visual-token keys.
        frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$visual_system")
        if ! echo "$frontmatter" | grep -qE '^(palette|typography|layout|image_treatment|ui_chrome):'; then
          needs_migration=1
        fi
      fi
      if [ "$needs_migration" -eq 1 ]; then
        if [ "$first" != "---" ]; then
          echo "[WARN] brand $slug: visual-system.md is prose-shaped, brand-layer tokens are not contributing to the resolver merge."
        else
          echo "[WARN] brand $slug: visual-system.md is missing visual-token frontmatter, brand-layer tokens are not contributing to the resolver merge."
        fi
        echo "       Run: ./scripts/migrate_brand_visual_system.sh --brand $slug"
      fi
    fi

    # v0.6.1: lint brand-voice.md for kit-default rule violations.
    brand_voice="$brand_dir/brand-voice.md"
    if [ -f "$brand_voice" ]; then
      lint_status=0
      lint_out=$("$REPO_ROOT/scripts/lint_script.sh" "$brand_voice" 2>&1) || lint_status=$?
      if [ "$lint_status" -ne 0 ]; then
        while IFS= read -r line; do
          case "$line" in
            *"["*"]"*)
              rule_id=$(echo "$line" | sed -E 's/.*\[([^]]+)\].*/\1/')
              echo "[WARN] brand $slug: brand-voice.md violates $rule_id"
              ;;
          esac
        done <<< "$lint_out"
      fi
      unset lint_status
    fi
  done
else
  check WARN "no brands found at $BRANDS_ROOT: run scripts/init_brand.sh <slug>"
fi

exit "$EXIT"
