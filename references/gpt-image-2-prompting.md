# gpt-image-2 Prompting Reference

Constraints, sizes, and known gotchas for the OpenAI gpt-image-2 image generation API.

## Hard constraints

- **Both width and height must be divisible by 16.** Anything else returns `400 Invalid size 'WxH'`.
- The `response_format` parameter is rejected as `unknown_parameter`. The model returns base64 by default.
- High-quality generation can take 60–180 seconds per image. Use a 300s+ urlopen timeout.
- The response shape is `{"data": [{"b64_json": "..."}]}` — single field, base64-encoded PNG.

## Recommended sizes

These are 16-divisible and map cleanly to platform requirements.

| Use case | Size | Aspect | Notes |
|----------|------|--------|-------|
| Square feed (LinkedIn / IG) | 1024×1024 | 1:1 | Default canonical size |
| LinkedIn carousel (portrait) | 1024×1536 | 2:3 | OpenAI canonical portrait |
| Stories / Reels / TikTok | 1024×1792 | ~9:15.75 | Closest 16-divisible to 9:16 |
| Landscape | 1536×1024 | 3:2 | OpenAI canonical landscape |

## Why not 1080×1080?

LinkedIn and Instagram both render assets at 1080px native, so that was the historical "best" size for social. gpt-image-2 doesn't accept it (1080 / 16 = 67.5). Use 1024×1024 — both platforms upscale 1024 cleanly with no visible quality loss in feed.

If you need exact 1080px assets, generate at 1024×1024 and upscale post-generation with an external tool (ffmpeg, ImageMagick).

## Quality / cost

- `quality: low` — fastest, cheapest (~$0.01–0.02 per image). Good for evals, dry-run pipeline checks, prompt iteration.
- `quality: medium` — balanced.
- `quality: high` — best output, ~$0.04–0.07 per 1024×1024. Use for production.

A 14-slide carousel (7 slides × 2 sizes) at high quality runs ~$0.60–1.00 and ~25–40 minutes wall-clock.

## Auth

Set `OPENAI_API_KEY` in your environment. The wrapper at `skills/branded-carousel/scripts/gpt_image_2.py` reads it from env. Do not commit keys — kit's `.gitignore` covers `.env` and `*.key`.

## SSL on macOS Python.framework

Python installed from python.org as Python.framework on macOS may fail TLS handshakes against `api.openai.com` with `CERTIFICATE_VERIFY_FAILED` because no system CA bundle is wired in by default. Fix:

```bash
export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
```

Add this to your shell rc, or wrap the kit's scripts in a launcher that sets it. `install.sh` does NOT set this for you because it's environment-specific.

## Retry semantics

The wrapper retries on:
- HTTP 429 (rate limit)
- HTTP 5xx (500/502/503/504)
- `URLError`, `TimeoutError`, generic `OSError`

Default retry delays: `[2, 5, 15]` seconds. Override via `--retry-delays` if calling programmatically.

## Save-first principle

Generated PNGs are written to disk immediately after the API response. Never reference an ephemeral provider URL as the canonical artifact — gpt-image-2 returns base64 inline, so this is enforced naturally, but downstream code should never rely on re-fetching from any URL.
