#!/usr/bin/env bash
# generate_concepts.sh: Stage 1 of concept-generator pipeline.
#
# Loads brand corpus, reads trend input, packages context for the host agent,
# and writes runs/<date>/concepts.md after the agent generates ranked concepts.
#
# In dry-run mode (no host-agent integration), writes a minimal concepts.md
# placeholder with three concepts so downstream stages have something to
# consume. The placeholder is replaced with real output when invoked from
# the daily-loop with a host agent.
#
# Exit codes:
#   0 ok
#   1 brand or trend-input not found
#   2 usage error

set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: generate_concepts.sh --brand <slug> --trend-input <path> --output <run-dir> [--mode <interactive|autopilot>] [--count <N>] [--dry-run]
EOF
  exit 2
}

BRAND=""
TREND_INPUT=""
OUTPUT_DIR=""
MODE="interactive"
COUNT="7"
DRY_RUN=0
BRANDS_ROOT="${BRANDS_ROOT:-$HOME/Documents/GitHub/slideshow-brands}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --brand) BRAND="$2"; shift 2 ;;
    --trend-input) TREND_INPUT="$2"; shift 2 ;;
    --output) OUTPUT_DIR="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --count) COUNT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --brands-root) BRANDS_ROOT="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "[ERR] unknown arg: $1" >&2; usage ;;
  esac
done

[[ -z "$BRAND" || -z "$TREND_INPUT" || -z "$OUTPUT_DIR" ]] && usage

if [[ ! -d "$BRANDS_ROOT/$BRAND" ]]; then
  echo "[ERR] brand '$BRAND' not found at $BRANDS_ROOT/$BRAND" >&2
  exit 1
fi
if [[ ! -f "$TREND_INPUT" ]]; then
  echo "[ERR] trend-input not found: $TREND_INPUT" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

# Build the context bundle for the host agent.
CONTEXT_JSON="$OUTPUT_DIR/concept-context.json"

PYTHONPATH="$REPO_ROOT" python3 - "$BRAND" "$BRANDS_ROOT" "$TREND_INPUT" "$MODE" "$COUNT" "$CONTEXT_JSON" <<'PY'
import json
import os
import sys

from lib.concept_corpus import load_brand_corpus

TREND_INPUT_MAX_BYTES = 256_000

brand, brands_root, trend_input, mode, count, out = sys.argv[1:7]

if os.path.getsize(trend_input) > TREND_INPUT_MAX_BYTES:
    print(
        f"[ERR] trend-input exceeds {TREND_INPUT_MAX_BYTES} bytes; trim or split it.",
        file=sys.stderr,
    )
    sys.exit(1)

bundle = load_brand_corpus(brand, brands_root=brands_root)

with open(trend_input) as f:
    trend = f.read()

context = {
    "brand": brand,
    "mode": mode,
    "count": int(count),
    "trend_input": trend,
    "voice_profile": bundle.voice_profile,
    "brand_voice_rules": bundle.brand_voice_rules,
    "is_thin_corpus": bundle.is_thin,
    "deliverable_count": len(bundle.recent_deliverables),
    "deliverable_names": [name for name, _ in bundle.recent_deliverables],
    "sources": bundle.sources,
}

with open(out, "w") as f:
    json.dump(context, f, indent=2)
PY

CONCEPTS_MD="$OUTPUT_DIR/concepts.md"

if [[ "$DRY_RUN" -eq 1 ]]; then
  cat > "$CONCEPTS_MD" <<EOF
# Concepts (dry-run placeholder)

> dry-run mode: this is a placeholder. Real concepts are generated when
> the host agent reads concept-context.json and prompts.json's
> concept_generation template.

## Concept 1 (rank: 1, concept_score: 7.5, claims_personal_fact: false)

**Format:** narrative
**Close action:** save
**Arc:** placeholder concept for dry-run validation.
**Why this works:** placeholder.

### Hook variants
1. (observation, shock 35) "scroll your feed and count the patterns. they repeat."
2. (single_claim, shock 30) "i found the four patterns in 30 minutes."
3. (question, shock 28) "what does your feed look like once you spot the patterns?"

## Concept 2 (rank: 2, concept_score: 7.0, claims_personal_fact: false)

**Format:** numbered_diagnostic
**Close action:** save
**Arc:** placeholder.
**Why this works:** placeholder.

### Hook variants
1. (observation, shock 32) "the 3 tells of every X. once you see them you can't unsee."

## Concept 3 (rank: 3, concept_score: 6.5, claims_personal_fact: true)

**Format:** narrative
**Close action:** save
**Arc:** placeholder claiming personal fact (autopilot will down-rank).
**Why this works:** placeholder.

### Hook variants
1. (scene, shock 38) "tuesday morning. i did the audit."
EOF
  echo "[OK] dry-run concepts written: $CONCEPTS_MD"
  exit 0
fi

# Real (non-dry-run) flow: the host agent reads concept-context.json and
# prompts.json's concept_generation template and writes concepts.md.
# This script's job ends here; the agent takes over.

cat <<EOF
[INFO] context bundle written: $CONTEXT_JSON
[INFO] host agent should now read $REPO_ROOT/skills/concept-generator/prompts.json
       and use the concept_generation template with the context bundle to
       write $CONCEPTS_MD.
EOF
