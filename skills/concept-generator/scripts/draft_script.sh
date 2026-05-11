#!/usr/bin/env bash
# draft_script.sh: Stage 3 of concept-generator pipeline.
#
# Reads concept-pick.md, prompts host agent (via prompts.json templates) for
# scene-elicitation (interactive mode + claims_personal_fact: true), drafts
# script.md, runs voice_lint + format_lint + save_filter pre-output, writes
# concept-meta.json artifact.
#
# In dry-run, writes a placeholder script.md and concept-meta.json.
#
# Exit codes:
#   0 ok
#   1 run-dir / concept-pick.md not found, lint failures (without bypass)
#   2 usage error

set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: draft_script.sh --run-dir <path> [--mode <interactive|autopilot>] [--no-lint] [--no-format-check] [--no-save-filter] [--dry-run]
EOF
  exit 2
}

RUN_DIR=""
MODE="interactive"
NO_LINT=0
NO_FORMAT_CHECK=0
NO_SAVE_FILTER=0
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --no-lint) NO_LINT=1; shift ;;
    --no-format-check) NO_FORMAT_CHECK=1; shift ;;
    --no-save-filter) NO_SAVE_FILTER=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) echo "[ERR] unknown arg: $1" >&2; usage ;;
  esac
done

[[ -z "$RUN_DIR" ]] && usage

if [[ ! -d "$RUN_DIR" ]]; then
  echo "[ERR] run-dir not found: $RUN_DIR" >&2
  exit 1
fi
PICK_MD="$RUN_DIR/concept-pick.md"
if [[ ! -f "$PICK_MD" ]]; then
  echo "[ERR] concept-pick.md not found in $RUN_DIR" >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

CMD=(python3 -m lib.draft_script_meta --run-dir "$RUN_DIR" --mode "$MODE")
[[ "$NO_LINT" -eq 1 ]] && CMD+=("--no-lint")
[[ "$NO_FORMAT_CHECK" -eq 1 ]] && CMD+=("--no-format-check")
[[ "$NO_SAVE_FILTER" -eq 1 ]] && CMD+=("--no-save-filter")
[[ "$DRY_RUN" -eq 1 ]] && CMD+=("--dry-run")

PYTHONPATH="$REPO_ROOT" "${CMD[@]}"
