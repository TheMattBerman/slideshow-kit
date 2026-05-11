#!/usr/bin/env bash
# pick_concept.sh: Stage 2 of concept-generator pipeline.
#
# Reads concepts.md, picks one concept (operator-driven via --concept N or
# autopilot via --mode autopilot), writes concept-pick.md.
#
# Exit codes:
#   0 ok
#   1 run-dir not found / no autopilot-safe concept
#   2 usage error / out-of-range concept

set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: pick_concept.sh --run-dir <path> [--concept <N>] [--mode <interactive|autopilot>]
EOF
  exit 2
}

RUN_DIR=""
CONCEPT_N=""
MODE="interactive"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --concept) CONCEPT_N="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "[ERR] unknown arg: $1" >&2; usage ;;
  esac
done

[[ -z "$RUN_DIR" ]] && usage

CONCEPTS_MD="$RUN_DIR/concepts.md"
if [[ ! -f "$CONCEPTS_MD" ]]; then
  echo "[ERR] concepts.md not found at $CONCEPTS_MD" >&2
  exit 1
fi

PICK_MD="$RUN_DIR/concept-pick.md"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

PYTHONPATH="$REPO_ROOT" python3 - "$CONCEPTS_MD" "$PICK_MD" "$MODE" "${CONCEPT_N:-}" <<'PY'
import re
import sys

concepts_path, pick_path, mode, concept_n = sys.argv[1:5]

with open(concepts_path) as f:
    text = f.read()

header_re = re.compile(
    r"^## Concept (\d+).*?claims_personal_fact:\s*(true|false)\)",
    re.MULTILINE | re.IGNORECASE,
)
matches = list(header_re.finditer(text))
if not matches:
    print(f"[ERR] no concept sections found in {concepts_path}", file=sys.stderr)
    sys.exit(1)

concepts = []
for i, m in enumerate(matches):
    start = m.start()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    n = int(m.group(1))
    personal = m.group(2).lower() == "true"
    body = text[start:end].rstrip() + "\n"
    concepts.append({"n": n, "personal": personal, "body": body})

picked = None
if mode == "autopilot":
    safe = [c for c in concepts if not c["personal"]]
    if not safe:
        print("[ERR] no autopilot-safe concept (all claim personal facts).", file=sys.stderr)
        sys.exit(1)
    picked = safe[0]
else:
    if not concept_n:
        print("[ERR] interactive mode requires --concept N", file=sys.stderr)
        sys.exit(2)
    try:
        target = int(concept_n)
    except ValueError:
        print(f"[ERR] --concept must be an integer, got: {concept_n}", file=sys.stderr)
        sys.exit(2)
    candidates = [c for c in concepts if c["n"] == target]
    if not candidates:
        print(f"[ERR] concept {target} out of range (have: {[c['n'] for c in concepts]})",
              file=sys.stderr)
        sys.exit(2)
    picked = candidates[0]

with open(pick_path, "w") as f:
    f.write(f"# Picked concept (mode: {mode})\n\n")
    f.write(picked["body"])

print(f"[OK] picked Concept {picked['n']} -> {pick_path}")
PY
