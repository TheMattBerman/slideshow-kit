#!/usr/bin/env python3
"""
gpt-image-2 wrapper. Save-first. Retry on transient errors. Dry-run mode for cost-free dev.

Stdlib only, no third-party deps.
"""
import argparse
import base64
import json
import os
import ssl
import subprocess
import sys
import time
from typing import List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    import certifi
    HAS_CERTIFI = True
except ImportError:
    certifi = None  # type: ignore[assignment]
    HAS_CERTIFI = False

API_URL = "https://api.openai.com/v1/images/generations"
EDITS_URL = "https://api.openai.com/v1/images/edits"
MODEL = "gpt-image-2"
DEFAULT_RETRY_DELAYS = [2, 5, 15]


def _is_ssl_cert_error(err: BaseException) -> bool:
    """True iff err is a urllib URLError whose reason is an SSL cert verify failure."""
    if isinstance(err, URLError):
        reason = getattr(err, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return True
        if isinstance(reason, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(reason):
            return True
    if isinstance(err, ssl.SSLCertVerificationError):
        return True
    if isinstance(err, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(err):
        return True
    return False


def _open_with_cert_fallback(req, timeout):
    """Open a urllib request; on SSL cert verify error, retry once with certifi bundle.

    If certifi is not installed, the original SSL error is re-raised with a hint
    pointing operators at the install command.
    """
    try:
        return urlopen(req, timeout=timeout)
    except (URLError, ssl.SSLError) as e:
        if not _is_ssl_cert_error(e):
            raise
        if not HAS_CERTIFI:
            print(
                "[FAIL] SSL certificate verification failed and certifi is not "
                "installed. Install certifi (pip install certifi) to enable "
                "automatic SSL fallback.",
                file=sys.stderr,
            )
            raise
        print(
            "[INFO] SSL verify failed against system bundle; retrying with certifi.",
            file=sys.stderr,
        )
        assert certifi is not None  # narrowed by HAS_CERTIFI above
        ctx = ssl.create_default_context(cafile=certifi.where())
        return urlopen(req, timeout=timeout, context=ctx)


def _generate_via_edits(
    prompt: str,
    size: str,
    output_path: str,
    api_key: str,
    quality: str,
    reference_images: List[str],
    n: int = 1,
) -> List[str]:
    """POST to /v1/images/edits via curl multipart with one or more reference images.

    Returns a list of saved file paths. When n>1, paths are derived from output_path
    by inserting -N before the extension (e.g. slide.png -> slide-1.png, slide-2.png).
    """
    cmd = [
        "curl", "-sS", "--max-time", "600",
        "-X", "POST", EDITS_URL,
        "-H", f"Authorization: Bearer {api_key}",
        "-F", f"model={MODEL}",
    ]
    if HAS_CERTIFI and certifi is not None:
        # Always pass the certifi bundle when available so Python.org installs
        # don't trip on the default system bundle.
        cmd[2:2] = ["--cacert", certifi.where()]
    for ref in reference_images:
        cmd += ["-F", f"image[]=@{ref}"]
    cmd += [
        "-F", f"prompt={prompt}",
        "-F", f"size={size}",
        "-F", f"quality={quality}",
        "-F", f"n={n}",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = getattr(result, "stderr", "") or ""
        print(f"[FAIL] gpt-image-2 /edits curl exit {result.returncode}: {stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"[FAIL] gpt-image-2 /edits non-JSON response: {e}; raw={result.stdout[:500]!r}", file=sys.stderr)
        sys.exit(1)

    if "data" not in payload or not payload["data"]:
        print(f"[FAIL] gpt-image-2 /edits unexpected payload: {payload}", file=sys.stderr)
        sys.exit(1)

    saved: List[str] = []
    if n == 1:
        b64 = payload["data"][0]["b64_json"]
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64))
        saved.append(output_path)
    else:
        root, ext = os.path.splitext(output_path)
        for i, item in enumerate(payload["data"], start=1):
            p = f"{root}-{i}{ext}"
            with open(p, "wb") as f:
                f.write(base64.b64decode(item["b64_json"]))
            saved.append(p)
    return saved


def generate(
    prompt: str,
    size: str,
    output_path: str,
    api_key: Optional[str],
    dry_run: bool = False,
    retry_delays: Optional[List[int]] = None,
    quality: str = "high",
    reference_images: Optional[List[str]] = None,
    n: int = 1,
) -> dict:
    """Generate one or more images. Returns metadata dict.

    When `reference_images` is non-empty (and not dry-run), uses
    POST /v1/images/edits via curl multipart for character-likeness preservation.
    Otherwise uses the JSON /v1/images/generations path (n must be 1 on that path).
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    refs = list(reference_images) if reference_images else []

    if dry_run:
        prompt_path = output_path.replace(".png", ".prompt.txt")
        with open(prompt_path, "w") as f:
            f.write(f"size: {size}\nmodel: {MODEL}\nquality: {quality}\nn: {n}\n")
            if refs:
                f.write(f"reference_images: {refs}\n")
            f.write(f"\n{prompt}\n")
        return {
            "dry_run": True,
            "prompt_path": prompt_path,
            "size": size,
            "reference_images": refs,
            "n": n,
        }

    if not api_key:
        print("[FAIL] OPENAI_API_KEY required when not in dry-run mode", file=sys.stderr)
        sys.exit(1)

    if refs:
        paths = _generate_via_edits(
            prompt=prompt,
            size=size,
            output_path=output_path,
            api_key=api_key,
            quality=quality,
            reference_images=refs,
            n=n,
        )
        return {
            "dry_run": False,
            "model": MODEL,
            "size": size,
            "quality": quality,
            "output_path": output_path if n == 1 else None,
            "output_paths": paths,
            "endpoint": "edits",
            "reference_images": refs,
            "n": n,
        }

    if n != 1:
        print("[FAIL] /generations path requires n=1; pass reference_images for batch", file=sys.stderr)
        sys.exit(1)

    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "n": 1,
    }).encode("utf-8")

    req = Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    delays = retry_delays if retry_delays is not None else DEFAULT_RETRY_DELAYS
    last_err = None
    for attempt, delay in enumerate([0] + delays):
        if delay:
            time.sleep(delay)
        try:
            with _open_with_cert_fallback(req, timeout=300) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504) and attempt < len(delays):
                continue
            print(f"[FAIL] gpt-image-2 HTTPError {e.code}: {e.reason}", file=sys.stderr)
            sys.exit(1)
        except (URLError, TimeoutError, OSError) as e:
            last_err = e
            if attempt < len(delays):
                continue
            print(f"[FAIL] gpt-image-2 transient error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"[FAIL] gpt-image-2 retry exhausted: {last_err}", file=sys.stderr)
        sys.exit(1)

    b64 = payload["data"][0]["b64_json"]
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(b64))

    return {
        "dry_run": False,
        "model": MODEL,
        "size": size,
        "quality": quality,
        "output_path": output_path,
        "endpoint": "generations",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--size", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quality", default="high")
    ap.add_argument(
        "--reference-image",
        action="append",
        default=[],
        help="Path to a reference image for character likeness. Repeat for multiple.",
    )
    args = ap.parse_args()

    result = generate(
        prompt=args.prompt,
        size=args.size,
        output_path=args.output,
        api_key=os.environ.get("OPENAI_API_KEY"),
        dry_run=args.dry_run,
        quality=args.quality,
        reference_images=args.reference_image,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
