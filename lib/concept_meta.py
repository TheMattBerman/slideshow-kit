"""Read and write runs/<dir>/concept-meta.json artifact.

Schema version 2 adds optional visual + word-cap fields:
- visual_hook (str): one-sentence visual through-line.
- scene_direction_source (str): "stage_3" or "renderer_fallback".
- word_cap_overridden (bool): True if a per-role word cap override was
  applied during this run.
- word_cap_source_path (str): path to the style.yaml that supplied the
  override (if any).

Schema version 1 records remain readable; missing v2 fields surface as
None / absent keys.
"""

from __future__ import annotations

import json
import os
from typing import Any

from lib.visual_director import SCENE_DIRECTION_SOURCES

CONCEPT_META_SCHEMA_VERSION = 2

# concept_meta also accepts empty/null (renderer writes "" when no scene direction).
_VALID_SCENE_SOURCES = set(SCENE_DIRECTION_SOURCES) | {"", None}


# Skip-flags (save_filter_skipped, lint_skipped, format_check_skipped) and
# trend_id_or_topic are intentionally optional. They record runtime decisions
# that may be absent in older / minimal records.
REQUIRED_FIELDS = {
    "format",
    "close_action",
    "hook_pattern",
    "hook_score",
    "concept_score",
    "claims_personal_fact",
    "concept_id",
    "brand",
    "timestamp",
}


def _validate(meta: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS - set(meta.keys())
    if missing:
        raise ValueError(f"concept-meta missing required fields: {sorted(missing)}")
    if "scene_direction_source" in meta:
        val = meta["scene_direction_source"]
        if val not in _VALID_SCENE_SOURCES:
            raise ValueError(
                "scene_direction_source must be one of "
                f"{sorted(s for s in _VALID_SCENE_SOURCES if s)} "
                f"(or empty / null); got: {val!r}"
            )


def write_meta(run_dir: str, meta: dict[str, Any]) -> str:
    """Write runs/<dir>/concept-meta.json. Returns artifact path."""
    _validate(meta)
    out = dict(meta)
    out["_schema_version"] = CONCEPT_META_SCHEMA_VERSION

    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "concept-meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    return path


def read_meta(run_dir: str) -> dict[str, Any]:
    """Read runs/<dir>/concept-meta.json. Returns parsed dict."""
    path = os.path.join(run_dir, "concept-meta.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
