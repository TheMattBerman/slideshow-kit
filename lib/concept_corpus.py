"""Brand corpus loader for concept-generator skill.

Walks a brand's well-known paths to gather voice profile, brand-voice rules,
and recent deliverables. Falls back to kit defaults when corpus is thin.
"""

from __future__ import annotations

import os
import re
from typing import NamedTuple, Optional


_BRAND_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class CorpusBundle(NamedTuple):
    voice_profile: str
    brand_voice_rules: str
    recent_deliverables: list[tuple[str, str]]
    is_thin: bool
    sources: dict[str, str]


KIT_DEFAULT_VOICE = """\
# Kit default voice profile

The brand has no voice corpus. Use these conservative defaults:

- lowercase prose; punchy short sentences
- single-claim hooks (one emotional pull per hook)
- dated specifics: prefer "tuesday" or "last november" to "recently"
- name frameworks in two or three words: "the audit move", "the receipt rule"
- no em dashes; no aphoristic openers ("the truth is", "here's the thing")
- close with a clear save / share / comment ask
"""

KIT_DEFAULT_BRAND_VOICE = """\
# Kit default brand-voice rules

## Avoid
- "synergy"
- "circle back"
- "deep dive"
- "leverage"
"""


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _resolve_brands_root(brands_root: Optional[str]) -> str:
    if brands_root:
        return brands_root
    env = os.environ.get("BRANDS_ROOT")
    if env:
        return env
    return os.path.expanduser("~/Documents/GitHub/slideshow-brands")


def _gather_deliverables(brand_dir: str) -> list[tuple[str, str]]:
    """Return up to 5 most-recent (filename, content) pairs."""
    candidates: list[tuple[float, str, str]] = []
    recent_dir = os.path.join(brand_dir, "deliverables", "recent")
    deliverables_dir = os.path.join(brand_dir, "deliverables")
    if os.path.isdir(recent_dir):
        scan_dirs = [recent_dir]
    elif os.path.isdir(deliverables_dir):
        scan_dirs = [deliverables_dir]
    else:
        return []

    for sd in scan_dirs:
        for root, _, files in os.walk(sd):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                full = os.path.join(root, fname)
                try:
                    mtime = os.path.getmtime(full)
                except OSError:
                    continue
                candidates.append((mtime, fname, full))

    candidates.sort(reverse=True)
    out: list[tuple[str, str]] = []
    for _mtime, fname, full in candidates[:5]:
        try:
            out.append((fname, _read(full)))
        except OSError:
            continue
    return out


def load_brand_corpus(brand_slug: str, brands_root: Optional[str] = None) -> CorpusBundle:
    """Load brand corpus from well-known paths with fallbacks.

    Lookup order:
    1. brands/<slug>/voice-profile.md (preferred)
    2. brands/<slug>/brand-voice.md (fallback for voice)
    3. brands/<slug>/deliverables/recent/*.md (last 5 by mtime)
    4. brands/<slug>/deliverables/**/*.md (last 5 by mtime if recent/ missing)
    5. KIT_DEFAULT_VOICE / KIT_DEFAULT_BRAND_VOICE (constants above)
    """
    if not _BRAND_SLUG_RE.match(brand_slug):
        raise ValueError(
            f"brand_slug must match [a-z0-9][a-z0-9_-]{{0,63}}; got: {brand_slug!r}"
        )
    root = _resolve_brands_root(brands_root)
    brand_dir = os.path.join(root, brand_slug)
    # Defense-in-depth: confirm brand_dir lies under root after symlink resolution.
    real_root = os.path.realpath(root)
    real_brand = os.path.realpath(brand_dir)
    if os.path.commonpath([real_brand, real_root]) != real_root:
        raise ValueError(
            f"brand_slug {brand_slug!r} resolves outside brands_root"
        )
    if not os.path.isdir(brand_dir):
        raise FileNotFoundError(f"brand '{brand_slug}' not found at {brand_dir}")

    sources: dict[str, str] = {}

    voice_profile_path = os.path.join(brand_dir, "voice-profile.md")
    brand_voice_path = os.path.join(brand_dir, "brand-voice.md")

    if os.path.isfile(voice_profile_path):
        voice_profile = _read(voice_profile_path)
        sources["voice_profile"] = voice_profile_path
    elif os.path.isfile(brand_voice_path):
        voice_profile = _read(brand_voice_path)
        sources["voice_profile"] = brand_voice_path
    else:
        voice_profile = KIT_DEFAULT_VOICE
        sources["voice_profile"] = "kit_default"

    if os.path.isfile(brand_voice_path):
        brand_voice_rules = _read(brand_voice_path)
        sources["brand_voice_rules"] = brand_voice_path
    else:
        brand_voice_rules = KIT_DEFAULT_BRAND_VOICE
        sources["brand_voice_rules"] = "kit_default"

    deliverables = _gather_deliverables(brand_dir)
    sources["deliverables_count"] = str(len(deliverables))

    voice_is_kit_default = sources["voice_profile"] == "kit_default"
    is_thin = voice_is_kit_default and not deliverables

    return CorpusBundle(
        voice_profile=voice_profile,
        brand_voice_rules=brand_voice_rules,
        recent_deliverables=deliverables,
        is_thin=is_thin,
        sources=sources,
    )
