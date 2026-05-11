"""Resolve style tokens through kit -> brand -> style layers."""

import copy
import json
import os
from typing import Any

from .design_md_parser import parse


KIT_DEFAULTS = {
    "palette": {
        "background": "#FFFFFF",
        "primary_accent": "#000000",
        "text": "#111111",
    },
    "typography": {
        "heading_family": "Inter",
        "heading_weight": "Bold",
        "heading_size_pt": 64,
        "body_family": "Inter",
        "body_weight": "Regular",
        "body_size_pt": 24,
    },
    "layout": {
        "grid_cols": 12,
        "hero_position": "center",
        "density": "medium",
    },
    "image_treatment": "none",
    "ui_chrome": {"pill_tags": False},
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Return a new dict where override keys win. Nested dicts merge recursively."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def resolve(brand_design_path: str, style_design_path: str) -> dict:
    """Resolve a flat token dict by merging kit defaults <- brand <- style.

    Style YAML tokens override brand YAML override kit defaults. The 'extends'
    key in the style YAML controls inheritance:
      - extends: brand (or absent) -> inherit from brand layer (default)
      - extends: kit -> skip brand layer, inherit from kit defaults only
    """
    brand = parse(brand_design_path).tokens
    style = parse(style_design_path).tokens

    extends = style.get("extends", "brand")
    if extends == "kit":
        merged = _deep_merge(KIT_DEFAULTS, style)
    else:
        merged = _deep_merge(KIT_DEFAULTS, brand)
        merged = _deep_merge(merged, style)

    # Strip the 'extends' key from the resolved bundle (it's an instruction, not a token).
    merged.pop("extends", None)
    return merged


# Schema version for resolved-tokens.json. Bump when the artifact shape changes.
RESOLVED_TOKENS_SCHEMA_VERSION = 1


def _flatten_keys(d: dict, prefix: str = "") -> dict:
    """Flatten nested dict to dotted keys: {'a': {'b': 1}} -> {'a.b': 1}."""
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten_keys(v, prefix=f"{key}."))
        else:
            out[key] = v
    return out


def _provenance(kit: dict, brand: dict, style: dict) -> dict:
    """Walk flattened keys, tag each with the highest layer that defined it."""
    style = {k: v for k, v in style.items() if k != "extends"}
    flat_kit = _flatten_keys(kit)
    flat_brand = _flatten_keys(brand)
    flat_style = _flatten_keys(style)
    out = {}
    for key in set(flat_kit) | set(flat_brand) | set(flat_style):
        if key in flat_style:
            out[key] = "style"
        elif key in flat_brand:
            out[key] = "brand"
        else:
            out[key] = "kit_default"
    return out


def resolve_with_artifact(
    brand_design_path: str, style_design_path: str, run_dir: str
) -> dict:
    """Resolve tokens and write <run_dir>/resolved-tokens.json with provenance."""
    brand_tokens = parse(brand_design_path).tokens if brand_design_path else {}
    style_tokens = parse(style_design_path).tokens if style_design_path else {}
    tokens = resolve(brand_design_path, style_design_path)

    # Honor `extends: kit`: brand layer was skipped, so it didn't contribute.
    extends = style_tokens.get("extends", "brand")
    effective_brand = {} if extends == "kit" else brand_tokens

    artifact: dict[str, Any] = dict(tokens)
    artifact["_schema_version"] = RESOLVED_TOKENS_SCHEMA_VERSION
    artifact["_layer_provenance"] = _provenance(KIT_DEFAULTS, effective_brand, style_tokens)

    os.makedirs(run_dir, exist_ok=True)
    artifact_path = os.path.join(run_dir, "resolved-tokens.json")
    with open(artifact_path, "w") as f:
        json.dump(artifact, f, indent=2, sort_keys=True, default=str)

    return tokens
