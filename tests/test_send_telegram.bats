#!/usr/bin/env bats

setup() {
  KIT_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  cd "$KIT_DIR"
  TMP="$(mktemp -d)"
  export TMP
  # Mock curl on PATH so the script never reaches the network
  cat > "$TMP/curl" <<'SH'
#!/usr/bin/env bash
# Mock curl: write request to TMP/curl-args.log, emit canned Telegram response
echo "$@" >> "${TMP:-/tmp}/curl-args.log"
case "${MOCK_CURL_MODE:-ok}" in
  ok)
    cat <<'JSON'
{"ok":true,"result":{"message_id":42,"chat":{"id":-1001234567890}}}
JSON
    exit 0
    ;;
  http_500)
    echo '{"ok":false,"error_code":500,"description":"server error"}'
    exit 22
    ;;
  network_fail)
    echo "curl: (6) Could not resolve host: api.telegram.org" >&2
    exit 6
    ;;
esac
SH
  chmod +x "$TMP/curl"
  export PATH="$TMP:$PATH"
  export TELEGRAM_BOT_TOKEN="test-token-1234"
}

teardown() {
  rm -rf "$TMP"
}

@test "send_telegram.sh exits 2 on missing flags" {
  run ./scripts/send_telegram.sh
  [ "$status" -eq 2 ]
}

@test "send_telegram.sh exits 2 when TELEGRAM_BOT_TOKEN unset" {
  unset TELEGRAM_BOT_TOKEN
  run ./scripts/send_telegram.sh --chat-id 100 --text "hi"
  [ "$status" -eq 2 ]
  [[ "$output" == *"TELEGRAM_BOT_TOKEN"* ]]
}

@test "send_telegram.sh happy path returns message_id and exits 0" {
  MOCK_CURL_MODE=ok run ./scripts/send_telegram.sh --chat-id 100 --text "hi"
  [ "$status" -eq 0 ]
  [[ "$output" == *"42"* ]]
}

@test "send_telegram.sh hits sendMessage endpoint with chat_id and text" {
  MOCK_CURL_MODE=ok run ./scripts/send_telegram.sh --chat-id 100 --text "hello bots"
  [ "$status" -eq 0 ]
  grep -q "sendMessage" "$TMP/curl-args.log"
  grep -q "chat_id=100" "$TMP/curl-args.log"
  grep -q "hello bots" "$TMP/curl-args.log"
}

@test "send_telegram.sh returns 11 on HTTP 500 from Telegram (decoupled, non-fatal exit code)" {
  MOCK_CURL_MODE=http_500 run ./scripts/send_telegram.sh --chat-id 100 --text "hi"
  [ "$status" -eq 11 ]
  [[ "$output" == *"telegram"* || "$output" == *"Telegram"* ]]
}

@test "send_telegram.sh returns 12 on network failure (decoupled)" {
  MOCK_CURL_MODE=network_fail run ./scripts/send_telegram.sh --chat-id 100 --text "hi"
  [ "$status" -eq 12 ]
}
