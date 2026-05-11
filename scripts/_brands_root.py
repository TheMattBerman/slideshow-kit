"""Resolve the brands root directory.

Resolution order:
1. $SLIDESHOW_BRANDS_ROOT env var
2. brands_root field in ~/.clawd/slideshow-kit/config.json
3. ./brands (CWD-relative, resolved to absolute)

Why: kit consumers don't all have ~/.clawd/. Default to a repo-local
brands/ dir (gitignored) for discoverability. Power users can pin to
any path via env or config for multi-tool workflows.
"""
import json
import os


def resolve_brands_root() -> str:
    """Return absolute path to the brands root directory."""
    root = os.environ.get("SLIDESHOW_BRANDS_ROOT", "")
    if not root:
        cfg = os.path.expanduser("~/.clawd/slideshow-kit/config.json")
        if os.path.isfile(cfg):
            try:
                with open(cfg) as f:
                    data = json.load(f)
                root = data.get("brands_root") or ""
            except (OSError, json.JSONDecodeError):
                root = ""
    if not root:
        root = "./brands"
    root = os.path.expanduser(root)
    if not os.path.isabs(root):
        root = os.path.abspath(root)
    return root


def brand_dir(brand: str) -> str:
    """Return absolute path to a specific brand's workspace dir."""
    return os.path.join(resolve_brands_root(), brand)
