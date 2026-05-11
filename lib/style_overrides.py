"""Per-style YAML override loader for format YAML defaults.

Style YAML lives at brands/<slug>/styles/<style>/style.yaml and is optional.
When present, word_count_override map supersedes format YAML's word_count_range
per role. Other keys reserved for future extensions.

Public surface:
    load_style_overrides(style_dir) -> dict[role -> (min, max)]
    merge_word_count_override(format_range, override) -> (min, max)
"""

from __future__ import annotations

import os
from typing import Optional

import yaml


def load_style_overrides(style_dir: str) -> dict[str, tuple[int, int]]:
    """Load word_count_override map from <style_dir>/style.yaml.

    Returns empty dict when:
    - style_dir does not exist
    - style.yaml not present in style_dir
    - style.yaml has no word_count_override section

    Raises ValueError on malformed entries.
    """
    if not os.path.isdir(style_dir):
        return {}
    yaml_path = os.path.join(style_dir, "style.yaml")
    if not os.path.isfile(yaml_path):
        return {}
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    raw = data.get("word_count_override", {}) or {}
    result: dict[str, tuple[int, int]] = {}
    for role, value in raw.items():
        if not isinstance(value, list) or len(value) != 2:
            raise ValueError(
                f"style.yaml: word_count_override[{role!r}] must be a "
                f"two-element list, got: {value!r}"
            )
        lo, hi = value
        if not isinstance(lo, int) or not isinstance(hi, int):
            raise ValueError(
                f"style.yaml: word_count_override[{role!r}] entries must "
                f"be integers, got: {value!r}"
            )
        if lo < 0 or hi < 0:
            raise ValueError(
                f"style.yaml: word_count_override[{role!r}] entries must "
                f"be non-negative, got: {value!r}"
            )
        if lo > hi:
            raise ValueError(
                f"style.yaml: word_count_override[{role!r}] min ({lo}) > "
                f"max ({hi})"
            )
        result[role] = (lo, hi)
    return result


def merge_word_count_override(
    format_range: tuple[int, int],
    override: Optional[tuple[int, int]],
) -> tuple[int, int]:
    """Return override when present, else format_range. Style wins."""
    return override if override is not None else format_range
