#!/usr/bin/env bats

# v0.5.0 case 17 uses `run --separate-stderr`, which requires bats >= 1.5.
bats_require_minimum_version 1.5.0

setup() {
  KIT_DIR="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
  cd "$KIT_DIR"
  TMP="$(mktemp -d)"
  export TMP
  export HOME="$TMP/home"
  export SLIDESHOW_BRANDS_ROOT="$TMP/brands"
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/acme"
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/config.json" <<'JSON'
{
  "brand": "acme",
  "mode": "draft",
  "lookback_days": 7,
  "posts_per_day": 1,
  "formats": ["branded"],
  "checkin": {"channel": "agent", "timeout_minutes": 30, "telegram_chat_id": null},
  "postiz": {"integration_ids": ["int-li-001", "int-ig-002"]},
  "created_on": "2026-05-04",
  "runs_history": 0
}
JSON
  mkdir -p "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/branded"
  echo "fake png" > "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/branded/slide-01-1080x1350.png"
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/post-01.json" <<'JSON'
{
  "caption": "test caption",
  "images": ["slide-01-1080x1350.png"],
  "platforms": ["linkedin", "instagram"]
}
JSON
  # Mock postiz CLI. Subcommand-aware:
  #   upload <path>  -> emit success header + JSON with .path URL
  #   posts:create   -> existing ok/fail behavior
  # MOCK_POSTIZ_MODE: ok (default), fail (posts:create errors), upload_fail (upload errors)
  cat > "$TMP/postiz" <<'SH'
#!/usr/bin/env bash
echo "postiz $@" >> "${TMP:-/tmp}/postiz-args.log"
SUB="${1:-}"
case "$SUB" in
  upload)
    case "${MOCK_POSTIZ_MODE:-ok}" in
      upload_fail)
        echo "Failed to upload file: api error 500" >&2
        exit 1
        ;;
      *)
        FILE_PATH="${2:-unknown}"
        BASE="$(basename "$FILE_PATH")"
        echo "File uploaded successfully!"
        echo "{"
        echo "  \"id\": \"upload-${BASE}\","
        echo "  \"name\": \"${BASE}\","
        echo "  \"path\": \"https://fake.postiz.media/${BASE}-uploaded.png\","
        echo "  \"thumbnail\": null,"
        echo "  \"alt\": null"
        echo "}"
        exit 0
        ;;
    esac
    ;;
  posts:create)
    case "${MOCK_POSTIZ_MODE:-ok}" in
      fail)
        echo "postiz: api error 500" >&2
        exit 1
        ;;
      *)
        echo '{"id":"post-abc-123","status":"draft"}'
        exit 0
        ;;
    esac
    ;;
  *)
    case "${MOCK_POSTIZ_MODE:-ok}" in
      ok|upload_fail)
        echo '{"id":"post-abc-123","status":"draft"}'
        exit 0
        ;;
      fail)
        echo "postiz: api error 500" >&2
        exit 1
        ;;
    esac
    ;;
esac
SH
  chmod +x "$TMP/postiz"
  export PATH="$TMP:$PATH"
}

teardown() {
  rm -rf "$TMP"
}

@test "publish_postiz.sh exits 2 on missing --brand" {
  run ./scripts/publish_postiz.sh --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 2 ]
}

@test "publish_postiz.sh exits 1 on unknown brand" {
  run ./scripts/publish_postiz.sh --brand nonexistent --posts /tmp
  [ "$status" -eq 1 ]
}

@test "publish_postiz.sh defaults to draft mode" {
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 0 ]
  grep -q -- "--draft" "$TMP/postiz-args.log" || grep -q "draft" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh autopilot mode requires explicit flag" {
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --mode autopilot --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 0 ]
  ! grep -q -- "--draft" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh emits one post per JSON file in posts dir" {
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/post-02.json" <<'JSON'
{"caption":"second","images":["slide-01-1080x1350.png"],"platforms":["linkedin"]}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 0 ]
  # Count posts:create invocations specifically. v0.5.0 introduces an upload step
  # per image, so a raw "^postiz " count would also include uploads.
  count=$(grep -c "posts:create" "$TMP/postiz-args.log" || true)
  [ "$count" -eq 2 ]
}

@test "publish_postiz.sh writes publish-log.json into posts dir" {
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 0 ]
  [ -f "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/publish-log.json" ]
}

@test "publish_postiz.sh fails non-zero when postiz CLI errors" {
  MOCK_POSTIZ_MODE=fail run ./scripts/publish_postiz.sh --brand acme --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 21 ]
}

@test "publish_postiz.sh --dry-run never invokes postiz CLI" {
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --dry-run --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 0 ]
  [ ! -f "$TMP/postiz-args.log" ] || ! grep -q "^postiz " "$TMP/postiz-args.log"
}

@test "publish_postiz.sh handles pretty-printed integration_ids array on multiple lines" {
  cat > "$SLIDESHOW_BRANDS_ROOT/acme/config.json" <<'JSON'
{
  "brand": "acme",
  "mode": "draft",
  "postiz": {
    "integration_ids": [
      "int-li-001",
      "int-ig-002"
    ]
  }
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04/"
  [ "$status" -eq 0 ]
  grep -q "int-li-001,int-ig-002" "$TMP/postiz-args.log"
}

# ---- v0.5.0 RED-state cases: image upload + scheduled_for honoring ----

@test "publish_postiz.sh uploads each image and assembles -m URLs" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  echo "fake png 1" > "$POSTS/branded/slide-01.png"
  echo "fake png 2" > "$POSTS/branded/slide-02.png"
  cat > "$POSTS/post-01.json" <<JSON
{
  "caption": "two slides",
  "images": ["branded/slide-01.png", "branded/slide-02.png"],
  "platforms": ["linkedin"]
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 0 ]
  grep -q "postiz upload .*branded/slide-01.png" "$TMP/postiz-args.log"
  grep -q "postiz upload .*branded/slide-02.png" "$TMP/postiz-args.log"
  grep -q "posts:create" "$TMP/postiz-args.log"
  grep -q -- "-m https://fake.postiz.media/slide-01.png-uploaded.png,https://fake.postiz.media/slide-02.png-uploaded.png" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh resolves images[] paths relative to POSTS_DIR" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  mkdir -p "$POSTS/branded"
  echo "fake png" > "$POSTS/branded/slide-01.png"
  cat > "$POSTS/post-01.json" <<JSON
{
  "caption": "nested path",
  "images": ["branded/slide-01.png"],
  "platforms": ["linkedin"]
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 0 ]
  # Path passed to upload must include the POSTS_DIR prefix (resolved absolute or
  # at minimum the branded/ subdir, not just the bare basename).
  grep -qE "postiz upload .+/branded/slide-01\.png" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh omits -m when images key is absent" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  cat > "$POSTS/post-01.json" <<'JSON'
{
  "caption": "no images key",
  "platforms": ["linkedin"]
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 0 ]
  ! grep -q "postiz upload" "$TMP/postiz-args.log"
  ! grep -qE "(^| )-m( |$)" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh omits -m when images[] is empty array" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  cat > "$POSTS/post-01.json" <<'JSON'
{
  "caption": "empty images",
  "images": [],
  "platforms": ["linkedin"]
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 0 ]
  ! grep -q "postiz upload" "$TMP/postiz-args.log"
  ! grep -qE "(^| )-m( |$)" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh honors scheduled_for in autopilot mode" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  cat > "$POSTS/post-01.json" <<'JSON'
{
  "caption": "scheduled autopilot",
  "images": ["slide-01-1080x1350.png"],
  "platforms": ["linkedin"],
  "scheduled_for": "2026-06-15T14:00:00Z"
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --mode autopilot --posts "$POSTS/"
  [ "$status" -eq 0 ]
  grep -q -- "-s 2026-06-15T14:00:00Z" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh honors scheduled_for in draft mode" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  cat > "$POSTS/post-01.json" <<'JSON'
{
  "caption": "scheduled draft",
  "images": ["slide-01-1080x1350.png"],
  "platforms": ["linkedin"],
  "scheduled_for": "2026-06-15T14:00:00Z"
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 0 ]
  grep -q -- "-s 2026-06-15T14:00:00Z" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh falls back to now+5min when scheduled_for absent" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  cat > "$POSTS/post-01.json" <<'JSON'
{
  "caption": "no schedule field",
  "images": ["slide-01-1080x1350.png"],
  "platforms": ["linkedin"]
}
JSON
  MOCK_POSTIZ_MODE=ok run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 0 ]
  grep -qE -- "-s 20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z" "$TMP/postiz-args.log"
}

@test "publish_postiz.sh falls back to now+5min on malformed scheduled_for and warns" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  cat > "$POSTS/post-01.json" <<'JSON'
{
  "caption": "bad schedule",
  "images": ["slide-01-1080x1350.png"],
  "platforms": ["linkedin"],
  "scheduled_for": "not-a-date"
}
JSON
  # bats `run` merges stdout+stderr by default, so a plain `2>` redirect on the
  # invocation gets swallowed. Use --separate-stderr (bats >=1.5) and assert on $stderr.
  MOCK_POSTIZ_MODE=ok run --separate-stderr ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 0 ]
  grep -qE -- "-s 20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z" "$TMP/postiz-args.log"
  ! grep -q -- "-s not-a-date" "$TMP/postiz-args.log"
  printf '%s' "$stderr" | grep -q "WARN"
}

@test "publish_postiz.sh upload failure fails the whole post (no posts:create call)" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  echo "fake png 1" > "$POSTS/branded/slide-01.png"
  echo "fake png 2" > "$POSTS/branded/slide-02.png"
  cat > "$POSTS/post-01.json" <<JSON
{
  "caption": "upload should fail",
  "images": ["branded/slide-01.png", "branded/slide-02.png"],
  "platforms": ["linkedin"]
}
JSON
  MOCK_POSTIZ_MODE=upload_fail run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 21 ]
  ! grep -q "posts:create" "$TMP/postiz-args.log"
  [ -f "$POSTS/publish-log.json" ]
  grep -q '"status":"failed"' "$POSTS/publish-log.json"
  grep -qi 'upload' "$POSTS/publish-log.json"
}

@test "publish_postiz.sh partial-batch upload failure isolates to its post" {
  POSTS="$SLIDESHOW_BRANDS_ROOT/acme/runs/2026-05-04"
  # post-01 has images that will fail to upload (because mock is upload_fail).
  echo "fake png 1" > "$POSTS/branded/slide-01.png"
  cat > "$POSTS/post-01.json" <<JSON
{
  "caption": "this one fails",
  "images": ["branded/slide-01.png"],
  "platforms": ["linkedin"]
}
JSON
  # post-02 has NO images so the upload step is skipped and posts:create succeeds
  # even under upload_fail mode (which only breaks the upload subcommand).
  cat > "$POSTS/post-02.json" <<'JSON'
{
  "caption": "this one publishes",
  "images": [],
  "platforms": ["linkedin"]
}
JSON
  MOCK_POSTIZ_MODE=upload_fail run ./scripts/publish_postiz.sh --brand acme --posts "$POSTS/"
  [ "$status" -eq 21 ]
  [ -f "$POSTS/publish-log.json" ]
  # publish-log.json should reference both posts
  grep -q "post-01.json" "$POSTS/publish-log.json"
  grep -q "post-02.json" "$POSTS/publish-log.json"
  grep -q '"status":"failed"' "$POSTS/publish-log.json"
  grep -q '"status":"ok"' "$POSTS/publish-log.json"
}
