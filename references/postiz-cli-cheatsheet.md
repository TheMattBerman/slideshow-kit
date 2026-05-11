# Postiz CLI Cheatsheet

The slideshow-kit relies on `postiz` CLI v2.0.13. This page lists the commands the kit invokes, their flags, and the response shapes the kit parses.

## Auth

```bash
postiz auth:login          # OAuth2 device flow, stores credentials locally
postiz auth:status         # prints current authentication status
postiz auth:logout
```

Alternative for CI / cron: set `POSTIZ_API_KEY` in the shell instead of running `auth:login`.

```bash
export POSTIZ_API_KEY="your_api_key"
```

### Self-hosted instances

If you run postiz on your own host (e.g. Synology, Railway, fly.io), point the CLI at it with `POSTIZ_API_URL`. The default is `https://api.postiz.com`. **The URL must include the `/api` path suffix.** Without it the CLI hits the Next.js auth UI and gets HTML back, which surfaces as `Unexpected token '<', "<!DOCTYPE "...` errors on every command.

```bash
export POSTIZ_API_URL=https://postiz.your-domain.com/api
```

This setting applies to all CLI calls (`auth:status`, `integrations:list`, `upload`, `posts:create`), not just one of them.

## Integrations

```bash
postiz integrations:list                # lists connected accounts: id, name, platform
postiz integrations:settings <id>       # show settings schema for an integration
```

Per-brand `integration_ids` live in `<brands_root>/<slug>/config.json` under `postiz.integration_ids`. Copy the relevant ids from `postiz integrations:list` after you connect each social account in the postiz UI.

### upload

```bash
postiz upload <file>
```

Positional `<file>` is required (absolute or relative path).

- Success (exit 0): two-part stdout. The first line is `✅ File uploaded successfully!`. The remainder is a JSON object with fields `id`, `name`, `path`, `thumbnail`, `alt`. The kit parses the URL with `tail -n +2 | jq -r .path`.
- Failure (exit 1): error written to stderr; stdout empty.

The `path` value is the URL postiz expects in `posts:create -m`.

## Posts

The kit calls `postiz posts:create` per post-*.json file. The wrapper `scripts/publish_postiz.sh` extracts the caption from each file, uploads any `images[]` entries, and assembles the call:

```bash
postiz posts:create \
  -c "<caption>" \
  -m "https://postiz.example.com/uploads/slide-01.png,https://postiz.example.com/uploads/slide-02.png" \
  -i "<integration_id_1>,<integration_id_2>" \
  -t draft \
  -s "2026-05-04T15:00:00Z"
```

Upload-then-post sequence (what the wrapper does internally):

```bash
URL=$(postiz upload ./slide-01.png | tail -n +2 | jq -r .path)
postiz posts:create -c "caption" -m "$URL" -i "id1,id2" -t draft -s "<iso>"
```

### Mode mapping (kit -> postiz)

| Kit mode | postiz `-t` value |
|---|---|
| `draft` (default for first 7 runs of any brand) | `draft` |
| `autopilot` | `schedule` |

`-s` (schedule date) is required by postiz even for drafts. The wrapper honors per-post `scheduled_for` when it is present and ISO-8601-valid (UTC, ending in `Z`); otherwise it falls back to `now + 5 minutes` (UTC).

### Other useful flags

- `-j, --json <path>`: alternative invocation that reads a complete post structure from a JSON file. The kit uses individual flags instead so caption / integrations / mode are visible in the args log.
- `--shortLink`: link shortening, default true.
- `--settings '<json>'`: platform-specific settings (Reddit subreddit, YouTube title/tags, X reply settings, etc.). Pass as a JSON string.

### post-*.json shape (kit-internal)

The kit's per-post file format, written by the carousel skills and read by `publish_postiz.sh`:

```json
{
  "caption": "string, body text per platform",
  "images": ["slide-01-1080x1350.png", "slide-02-1080x1350.png"],
  "platforms": ["linkedin", "instagram"],
  "scheduled_for": "2026-05-04T15:00:00Z"
}
```

As of v0.5.0, the wrapper uploads each `images[]` entry via `postiz upload` (paths are resolved relative to the posts dir), parses the resulting `.path` URLs into a comma-separated `-m` arg, and uses `scheduled_for` as the `-s` value when present and valid (ISO-8601 UTC, ending in `Z`). Empty or absent `images` produces a text-only post. Empty or invalid `scheduled_for` falls back to `now+5min` (a `[WARN]` line is emitted to stderr on malformed values). If any per-image upload fails, the whole post is marked `failed` in `publish-log.json` and `posts:create` is not called for that post; the wrapper continues to the next post and exits 21 if any failure occurred.

### Response shape

Success (exit 0) prints JSON to stdout:

```json
{"id": "post-abc-123", "status": "draft"}
```

Failure (exit non-zero): error written to stderr. The kit captures both into `publish-log.json`.

## Where the kit logs publishing

Every invocation of `scripts/publish_postiz.sh` writes `publish-log.json` into the run directory:

```
<brands_root>/<slug>/runs/<date>/publish-log.json
```

Shape:

```json
{
  "brand": "acme",
  "mode": "draft",
  "posts": [
    {"file": "post-01.json", "status": "ok", "response": "{...}"},
    {"file": "post-02.json", "status": "failed", "error": "..."}
  ]
}
```

## Common errors

- `postiz: api error 401`: token expired or `POSTIZ_API_KEY` invalid. Re-run `postiz auth:login` or rotate the key.
- `postiz: api error 429`: rate limit, wait and retry. The wrapper does not auto-retry; cron-driven daily loops naturally space out.
- `integration not found`: the integration id in `config.json` was disconnected in the postiz UI. Run `postiz integrations:list` and update.
- `Schedule date is required`: usually means `-s` was omitted; the wrapper always sets it, so this surfacing means a manual call.
- `Unexpected token '<', "<!DOCTYPE "...` from any CLI call: your `POSTIZ_API_URL` is missing the `/api` path suffix. Set it to `https://your-host/api`, not `https://your-host`. See the Self-hosted instances section above.

## Version pin

The kit was built against postiz CLI v2.0.13. Newer minor versions should be compatible. If a major bump arrives, run `doctor.sh` and review this cheatsheet against the latest `postiz <command> --help` output.
