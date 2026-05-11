#!/usr/bin/env bash
# lint_script.sh: lint a script file against kit-default + brand voice rules.
#
# Exit codes:
#   0 clean
#   1 violations found
#   2 usage error

set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: lint_script.sh <script-path> [--brand <slug>] [--brands-root <path>]

  <script-path>   path to the script file to lint
  --brand         optional brand slug; loads brand-voice.md ## Avoid section
  --brands-root   root for brand workspaces (default: $BRANDS_ROOT or ~/Documents/GitHub/slideshow-brands)
EOF
  exit 2
}

[[ $# -lt 1 ]] && usage

SCRIPT_PATH="$1"; shift || true
BRAND=""
BRANDS_ROOT="${BRANDS_ROOT:-$HOME/Documents/GitHub/slideshow-brands}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brand) BRAND="$2"; shift 2 ;;
    --brands-root) BRANDS_ROOT="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "[ERR] unknown arg: $1" >&2; usage ;;
  esac
done

[[ ! -f "$SCRIPT_PATH" ]] && { echo "[ERR] not found: $SCRIPT_PATH" >&2; exit 2; }

BRAND_VOICE_PATH=""
if [[ -n "$BRAND" ]]; then
  candidate="$BRANDS_ROOT/$BRAND/brand-voice.md"
  [[ -f "$candidate" ]] && BRAND_VOICE_PATH="$candidate"
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHONPATH="$REPO_ROOT" python3 - "$SCRIPT_PATH" "$BRAND_VOICE_PATH" <<'PY'
import sys
from lib.voice_lint import lint_text

script_path, brand_voice_path = sys.argv[1], (sys.argv[2] or None)
with open(script_path) as f:
    text = f.read()

violations = lint_text(text, brand_voice_path=brand_voice_path)
if not violations:
    sys.exit(0)

for v in violations:
    print(f"{script_path}:{v.line}:{v.column} [{v.rule_id}] {v.message}")
sys.exit(1)
PY
