#!/usr/bin/env bash
# send_telegram.sh: pure curl wrapper around the Telegram Bot API.
# Decoupled from postiz: never crashes the caller; uses distinct exit codes
# so the daily loop can detect "telegram failed" and fall through to autopilot.
#
# Exit codes:
#   0  : message sent, message_id printed on stdout
#   2  : usage error (missing flags or env)
#   11 : telegram returned non-ok (HTTP error or {"ok":false})
#   12 : network/curl failure (could not reach api.telegram.org)

set -euo pipefail

CHAT_ID=""
TEXT=""
FILES=""
PARSE_MODE="Markdown"

usage() {
  cat >&2 <<USAGE
usage: send_telegram.sh --chat-id <id> --text <message> [--files <comma-list>] [--parse-mode <Markdown|HTML>]

env: TELEGRAM_BOT_TOKEN (required)

exit codes: 0 ok, 2 usage, 11 telegram error, 12 network error
USAGE
  exit 2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --chat-id) CHAT_ID="${2:-}"; shift 2 ;;
    --text) TEXT="${2:-}"; shift 2 ;;
    --files) FILES="${2:-}"; shift 2 ;;
    --parse-mode) PARSE_MODE="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "unknown flag: $1" >&2; usage ;;
  esac
done

if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "[FAIL] TELEGRAM_BOT_TOKEN not set" >&2
  exit 2
fi
if [ -z "$CHAT_ID" ] || [ -z "$TEXT" ]; then
  usage
fi

API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"

# Use --data-urlencode for safe text. Capture body and exit code separately
# so a network failure (exit != 0) is distinguishable from a 200-with-error-body.
set +e
BODY="$(curl -sS \
  --data-urlencode "chat_id=${CHAT_ID}" \
  --data-urlencode "text=${TEXT}" \
  --data-urlencode "parse_mode=${PARSE_MODE}" \
  "$API")"
CURL_RC=$?
set -e

if [ "$CURL_RC" -ne 0 ]; then
  # Distinguish HTTP-level telegram error (body present) from total network failure (no body)
  if printf '%s' "$BODY" | grep -q '"ok"'; then
    echo "[WARN] telegram api error: $BODY" >&2
    exit 11
  fi
  echo "[WARN] telegram network failure (curl rc=${CURL_RC}); decoupled, caller will fall through" >&2
  exit 12
fi

# Extract ok and message_id with grep: stdlib only, no jq required at runtime
OK="$(printf '%s' "$BODY" | grep -o '"ok":[^,}]*' | head -n1 | sed 's/"ok"://; s/[^a-z]//g')"
if [ "$OK" != "true" ]; then
  echo "[WARN] telegram api error: $BODY" >&2
  exit 11
fi

MSG_ID="$(printf '%s' "$BODY" | grep -o '"message_id":[0-9]*' | head -n1 | sed 's/"message_id"://')"
if [ -z "$MSG_ID" ]; then
  echo "[WARN] telegram response missing message_id: $BODY" >&2
  exit 11
fi

# --files: documented but file upload deferred to v1.1; emit info line if used
if [ -n "$FILES" ]; then
  echo "[INFO] --files provided but media upload deferred to v1.1 (text-only sent)" >&2
fi

printf '%s\n' "$MSG_ID"
