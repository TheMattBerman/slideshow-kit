#!/usr/bin/env bash
# publish_postiz.sh: wrap postiz CLI v2.0.13 (upload + posts:create) to publish
# or draft a day's posts. Decoupled from telegram: failures here do not call
# telegram (the daily loop coordinates that). Distinct exit code 21 marks
# postiz failure.
#
# v0.5.0 adds:
#   - per-image upload step (postiz upload) before posts:create, with the
#     resulting URLs concatenated into a -m flag.
#   - honors a per-post scheduled_for ISO-8601 UTC field, falling back to
#     now+5min when absent or malformed.
#
# Exit codes:
#   0  : all posts handled successfully
#   1  : brand not found / config invalid
#   2  : usage error
#   21 : postiz CLI failure on at least one post (upload or posts:create)

set -euo pipefail

BRAND=""
POSTS_DIR=""
MODE=""           # draft (default) | autopilot
DRY_RUN=0

usage() {
  cat >&2 <<USAGE
usage: publish_postiz.sh --brand <slug> --posts <dir> [--mode draft|autopilot] [--dry-run]

reads:  <brands_root>/<slug>/config.json (postiz.integration_ids, mode default)
writes: <posts-dir>/publish-log.json

exit codes: 0 ok, 1 brand-not-found, 2 usage, 21 postiz-failure
USAGE
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --brand) BRAND="${2:-}"; shift 2 ;;
    --posts) POSTS_DIR="${2:-}"; shift 2 ;;
    --mode) MODE="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) echo "unknown flag: $1" >&2; usage ;;
  esac
done

if [ -z "$BRAND" ] || [ -z "$POSTS_DIR" ]; then
  usage
fi

BRANDS_ROOT="${SLIDESHOW_BRANDS_ROOT:-./brands}"
BRAND_DIR="$BRANDS_ROOT/$BRAND"
CONFIG="$BRAND_DIR/config.json"

if [ ! -f "$CONFIG" ]; then
  echo "[FAIL] brand workspace not found: $BRAND_DIR" >&2
  exit 1
fi
if [ ! -d "$POSTS_DIR" ]; then
  echo "[FAIL] posts dir not found: $POSTS_DIR" >&2
  exit 2
fi

# Strip any trailing slash from POSTS_DIR for clean path concatenation later.
POSTS_DIR="${POSTS_DIR%/}"

# Resolve mode: --mode flag wins, else config.mode, else "draft".
if [ -z "$MODE" ]; then
  MODE="$(grep -o '"mode":[^,}]*' "$CONFIG" | head -n1 | sed 's/.*"mode"://; s/[" ]//g')"
  MODE="${MODE:-draft}"
fi

case "$MODE" in
  draft|autopilot) ;;
  *) echo "[FAIL] invalid mode: $MODE (expected draft|autopilot)" >&2; exit 2 ;;
esac

# Map our mode to postiz -t value: draft -> draft, autopilot -> schedule.
POSTIZ_TYPE="schedule"
if [ "$MODE" = "draft" ]; then
  POSTIZ_TYPE="draft"
fi

# Pull integration_ids as a comma list. Stdlib parsing, no jq runtime dep here
# (preserved from v0.4.x for stability).
# Collapse newlines first so multi-line pretty-printed arrays are handled too.
INTEGRATIONS="$(tr '\n' ' ' < "$CONFIG" \
  | grep -o '"integration_ids"[[:space:]]*:[[:space:]]*\[[^]]*\]' \
  | head -n1 \
  | grep -o '\[[^]]*\]' \
  | tr -d '[]" ')"
if [ -z "$INTEGRATIONS" ]; then
  echo "[FAIL] brand has no postiz integration_ids in $CONFIG" >&2
  exit 1
fi

# postiz -s requires ISO 8601 UTC. Fallback schedule: 5 minutes in the future.
# date -u differs between BSD (macOS) and GNU; try both.
if SCHEDULE_AT="$(date -u -v+5M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)"; then
  :
else
  SCHEDULE_AT="$(date -u -d '+5 minutes' +%Y-%m-%dT%H:%M:%SZ)"
fi

extract_caption() {
  # Handles both multi-line and single-line JSON. jq would be cleaner but the
  # existing stdlib path is preserved for stability.
  local f="$1"
  cat "$f" | tr '\n' ' ' | grep -o '"caption"[[:space:]]*:[[:space:]]*"[^"]*"' \
    | head -n1 \
    | sed 's/"caption"[[:space:]]*:[[:space:]]*"//; s/"$//'
}

# ISO-8601 UTC validator: matches the same shape we emit for now+5min fallback.
ISO_UTC_RE='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'

LOG="$POSTS_DIR/publish-log.json"
TMP_LOG="$(mktemp)"
echo '{"brand":"'"$BRAND"'","mode":"'"$MODE"'","posts":[' > "$TMP_LOG"

POST_COUNT=0
FAILURES=0
FIRST=1
for post_json in "$POSTS_DIR"/post-*.json; do
  [ -f "$post_json" ] || continue
  POST_COUNT=$((POST_COUNT + 1))
  base="$(basename "$post_json")"
  CAPTION="$(extract_caption "$post_json")"
  [ -n "$CAPTION" ] || CAPTION="(no caption)"

  # Resolve scheduled_for. jq is an approved dep for v0.5.0.
  RAW_SCHED="$(jq -r '.scheduled_for // empty' "$post_json" 2>/dev/null || true)"
  POST_SCHED=""
  if [ -n "$RAW_SCHED" ]; then
    if printf '%s' "$RAW_SCHED" | grep -qE "$ISO_UTC_RE"; then
      POST_SCHED="$RAW_SCHED"
    else
      echo "[WARN] $base scheduled_for is malformed; using now+5min" >&2
    fi
  fi
  [ -n "$POST_SCHED" ] || POST_SCHED="$SCHEDULE_AT"

  if [ "$DRY_RUN" -eq 1 ]; then
    echo "[INFO] dry-run: would publish $base in $MODE mode to integrations: $INTEGRATIONS"
    [ "$FIRST" -eq 1 ] || echo "," >> "$TMP_LOG"
    echo '{"file":"'"$base"'","status":"dry-run"}' >> "$TMP_LOG"
    FIRST=0
    continue
  fi

  # Upload images, if any. Skip the whole loop when images is absent or empty.
  IMAGE_COUNT="$(jq -r '(.images // []) | length' "$post_json" 2>/dev/null || echo 0)"
  MEDIA_URLS=""
  UPLOAD_FAILED=0
  UPLOAD_ERR=""
  if [ "${IMAGE_COUNT:-0}" -gt 0 ]; then
    while IFS= read -r relpath; do
      [ -n "$relpath" ] || continue
      ABS_PATH="$POSTS_DIR/$relpath"
      set +e
      UPLOAD_OUT="$(postiz upload "$ABS_PATH" 2>&1)"
      URC=$?
      set -e
      if [ "$URC" -ne 0 ]; then
        UPLOAD_FAILED=1
        UPLOAD_ERR="upload failed for $relpath: $UPLOAD_OUT"
        break
      fi
      # Mock + real CLI both prefix the JSON with a non-JSON status line
      # ("File uploaded successfully!" or the same with a leading emoji).
      # Drop line 1, then jq the rest.
      URL="$(printf '%s\n' "$UPLOAD_OUT" | tail -n +2 | jq -r '.path' 2>/dev/null || true)"
      if [ -z "$URL" ] || [ "$URL" = "null" ]; then
        UPLOAD_FAILED=1
        UPLOAD_ERR="upload returned no .path for $relpath"
        break
      fi
      if [ -z "$MEDIA_URLS" ]; then
        MEDIA_URLS="$URL"
      else
        MEDIA_URLS="$MEDIA_URLS,$URL"
      fi
    done < <(jq -r '(.images // [])[]' "$post_json")
  fi

  [ "$FIRST" -eq 1 ] || echo "," >> "$TMP_LOG"
  FIRST=0

  if [ "$UPLOAD_FAILED" -eq 1 ]; then
    FAILURES=$((FAILURES + 1))
    SAFE="$(printf '%s' "$UPLOAD_ERR" | tr '\n' ' ' | sed 's/"/\\"/g')"
    echo '{"file":"'"$base"'","status":"failed","error":"'"$SAFE"'"}' >> "$TMP_LOG"
    echo "[FAIL] $base: $UPLOAD_ERR" >&2
    continue
  fi

  # Build posts:create command. Conditionally append -m only when we have URLs.
  CMD=(postiz posts:create -c "$CAPTION" -i "$INTEGRATIONS" -t "$POSTIZ_TYPE" -s "$POST_SCHED")
  if [ -n "$MEDIA_URLS" ]; then
    CMD+=(-m "$MEDIA_URLS")
  fi

  set +e
  RESPONSE="$("${CMD[@]}" 2>&1)"
  RC=$?
  set -e

  if [ "$RC" -ne 0 ]; then
    FAILURES=$((FAILURES + 1))
    SAFE="$(printf '%s' "$RESPONSE" | tr '\n' ' ' | sed 's/"/\\"/g')"
    echo '{"file":"'"$base"'","status":"failed","error":"'"$SAFE"'"}' >> "$TMP_LOG"
    echo "[FAIL] postiz failed on $base: $RESPONSE" >&2
  else
    SAFE="$(printf '%s' "$RESPONSE" | tr '\n' ' ' | sed 's/"/\\"/g')"
    echo '{"file":"'"$base"'","status":"ok","response":"'"$SAFE"'"}' >> "$TMP_LOG"
  fi
done

echo ']}' >> "$TMP_LOG"
mv "$TMP_LOG" "$LOG"

if [ "$POST_COUNT" -eq 0 ]; then
  echo "[WARN] no post-*.json files found in $POSTS_DIR" >&2
fi

if [ "$FAILURES" -gt 0 ]; then
  echo "[FAIL] $FAILURES of $POST_COUNT post(s) failed; see $LOG" >&2
  exit 21
fi

echo "[PASS] $POST_COUNT post(s) handled in $MODE mode"
