"""Tests for lib/style_resolver.py."""

import os

import pytest

from lib.style_resolver import resolve, KIT_DEFAULTS


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _make_design(tmp_path: str, name: str, yaml_block: str) -> str:
    """Helper: write a DESIGN.md with given yaml_block, return path."""
    p = os.path.join(tmp_path, f"{name}.md")
    _write(p, f"---\n{yaml_block}---\n\nBody\n")
    return p


def test_kit_defaults_only_when_brand_and_style_have_no_overrides(tmp_path):
    brand = _make_design(str(tmp_path), "brand", "name: brand\n")
    style = _make_design(str(tmp_path), "style", "name: style\n")
    tokens = resolve(brand, style)
    assert tokens["palette"]["background"] == KIT_DEFAULTS["palette"]["background"]
    assert tokens["typography"]["heading_family"] == KIT_DEFAULTS["typography"]["heading_family"]
    assert tokens["layout"]["grid_cols"] == KIT_DEFAULTS["layout"]["grid_cols"]


def test_brand_overrides_kit(tmp_path):
    brand = _make_design(str(tmp_path), "brand",
                         'palette:\n  background: "#FF0000"\n')
    style = _make_design(str(tmp_path), "style", "name: style\n")
    tokens = resolve(brand, style)
    assert tokens["palette"]["background"] == "#FF0000"


def test_style_overrides_brand(tmp_path):
    brand = _make_design(str(tmp_path), "brand",
                         'palette:\n  background: "#FF0000"\n')
    style = _make_design(str(tmp_path), "style",
                         'palette:\n  background: "#00FF00"\n')
    tokens = resolve(brand, style)
    assert tokens["palette"]["background"] == "#00FF00"


def test_style_overrides_brand_overrides_kit_per_key(tmp_path):
    """Each token resolves independently."""
    brand = _make_design(str(tmp_path), "brand",
                         'palette:\n  background: "#FF0000"\n  primary_accent: "#AA00AA"\n')
    style = _make_design(str(tmp_path), "style",
                         'palette:\n  background: "#00FF00"\n')
    tokens = resolve(brand, style)
    assert tokens["palette"]["background"] == "#00FF00"             # style wins
    assert tokens["palette"]["primary_accent"] == "#AA00AA"          # brand wins (style absent)
    assert tokens["palette"]["text"] == KIT_DEFAULTS["palette"]["text"]  # kit wins


def test_typography_partial_override(tmp_path):
    brand = _make_design(str(tmp_path), "brand",
                         'typography:\n  heading_family: "Custom"\n')
    style = _make_design(str(tmp_path), "style",
                         'typography:\n  heading_size_pt: 100\n')
    tokens = resolve(brand, style)
    assert tokens["typography"]["heading_family"] == "Custom"
    assert tokens["typography"]["heading_size_pt"] == 100
    assert tokens["typography"]["body_family"] == KIT_DEFAULTS["typography"]["body_family"]


def test_scalar_token_override(tmp_path):
    brand = _make_design(str(tmp_path), "brand",
                         'image_treatment: "minimal_flat_icons"\n')
    style = _make_design(str(tmp_path), "style", "name: style\n")
    tokens = resolve(brand, style)
    assert tokens["image_treatment"] == "minimal_flat_icons"


def test_extends_kit_skips_brand_layer(tmp_path):
    """A style with extends: kit ignores brand tokens."""
    brand = _make_design(str(tmp_path), "brand",
                         'palette:\n  background: "#FF0000"\n')
    style = _make_design(str(tmp_path), "style",
                         'extends: kit\nname: style\n')
    tokens = resolve(brand, style)
    assert tokens["palette"]["background"] == KIT_DEFAULTS["palette"]["background"]


def test_extends_brand_is_default(tmp_path):
    """No extends key means inherit from brand (default behavior)."""
    brand = _make_design(str(tmp_path), "brand",
                         'palette:\n  background: "#FF0000"\n')
    style = _make_design(str(tmp_path), "style", "name: style\n")
    tokens = resolve(brand, style)
    assert tokens["palette"]["background"] == "#FF0000"


def test_returns_flat_dict_not_nested_layers(tmp_path):
    brand = _make_design(str(tmp_path), "brand", "name: brand\n")
    style = _make_design(str(tmp_path), "style", "name: style\n")
    tokens = resolve(brand, style)
    assert "palette" in tokens
    assert "typography" in tokens
    assert "layers" not in tokens  # not exposing internal structure


def test_unknown_top_level_token_in_style_is_passed_through(tmp_path):
    """Forward-compatible: a new token in style YAML appears in resolved bundle."""
    brand = _make_design(str(tmp_path), "brand", "name: brand\n")
    style = _make_design(str(tmp_path), "style",
                         'name: style\nexperimental_thing: "yes"\n')
    tokens = resolve(brand, style)
    assert tokens["experimental_thing"] == "yes"


def test_brand_path_must_exist(tmp_path):
    style = _make_design(str(tmp_path), "style", "name: style\n")
    with pytest.raises(FileNotFoundError):
        resolve(os.path.join(str(tmp_path), "missing.md"), style)


def test_style_path_must_exist(tmp_path):
    brand = _make_design(str(tmp_path), "brand", "name: brand\n")
    with pytest.raises(FileNotFoundError):
        resolve(brand, os.path.join(str(tmp_path), "missing.md"))


def test_malformed_brand_yaml_propagates(tmp_path):
    brand = os.path.join(str(tmp_path), "brand.md")
    _write(brand, "---\nbroken: [unclosed\n---\nbody\n")
    style = _make_design(str(tmp_path), "style", "name: style\n")
    with pytest.raises(ValueError):
        resolve(brand, style)


def test_resolve_is_pure_function(tmp_path):
    """Same inputs, same output. No state leakage across calls."""
    brand = _make_design(str(tmp_path), "brand",
                         'palette:\n  background: "#111"\n')
    style = _make_design(str(tmp_path), "style", "name: style\n")
    a = resolve(brand, style)
    b = resolve(brand, style)
    assert a == b
    a["palette"]["background"] = "#999"
    c = resolve(brand, style)
    assert c["palette"]["background"] == "#111"  # mutating returned dict didn't affect next call


def test_kit_defaults_not_mutated_by_resolve(tmp_path):
    """Defensive copy: KIT_DEFAULTS is not mutated through resolve()."""
    original_bg = KIT_DEFAULTS["palette"]["background"]
    brand = _make_design(str(tmp_path), "brand",
                         'palette:\n  background: "#ZZZ"\n')
    style = _make_design(str(tmp_path), "style", "name: style\n")
    resolve(brand, style)
    assert KIT_DEFAULTS["palette"]["background"] == original_bg


import json

from lib.style_resolver import resolve_with_artifact


def test_resolve_with_artifact_writes_json(tmp_path):
    brand = tmp_path / "visual-system.md"
    brand.write_text(
        "---\n"
        "palette:\n"
        '  background: "#0D1117"\n'
        '  primary_accent: "#F43F5E"\n'
        "---\n\n"
        "# brand body\n"
    )
    style = tmp_path / "DESIGN.md"
    style.write_text(
        "---\n"
        "palette:\n"
        '  background: "#FFFFFF"\n'
        "---\n\n"
        "# style body\n"
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    tokens = resolve_with_artifact(str(brand), str(style), str(run_dir))

    assert tokens["palette"]["background"] == "#FFFFFF"
    assert tokens["palette"]["primary_accent"] == "#F43F5E"

    artifact = run_dir / "resolved-tokens.json"
    assert artifact.exists()
    parsed = json.loads(artifact.read_text())
    assert parsed["_schema_version"] == 1
    assert parsed["palette"]["background"] == "#FFFFFF"


def test_resolve_with_artifact_records_layer_provenance(tmp_path):
    brand = tmp_path / "visual-system.md"
    brand.write_text(
        "---\n"
        "palette:\n"
        '  primary_accent: "#F43F5E"\n'
        "---\n"
    )
    style = tmp_path / "DESIGN.md"
    style.write_text(
        "---\n"
        "palette:\n"
        '  background: "#FFFFFF"\n'
        "---\n"
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    resolve_with_artifact(str(brand), str(style), str(run_dir))

    parsed = json.loads((run_dir / "resolved-tokens.json").read_text())
    provenance = parsed["_layer_provenance"]
    assert provenance["palette.background"] == "style"
    assert provenance["palette.primary_accent"] == "brand"


def test_resolve_with_artifact_provenance_honors_extends_kit(tmp_path):
    brand = tmp_path / "visual-system.md"
    brand.write_text(
        "---\n"
        "palette:\n"
        '  primary_accent: "#F43F5E"\n'  # brand-only key
        "---\n"
    )
    style = tmp_path / "DESIGN.md"
    style.write_text(
        "---\n"
        'extends: kit\n'
        "palette:\n"
        '  background: "#FFFFFF"\n'
        "---\n"
    )
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    tokens = resolve_with_artifact(str(brand), str(style), str(run_dir))

    # extends: kit means brand layer is skipped, so primary_accent falls back to kit default.
    assert tokens["palette"]["primary_accent"] == "#000000"  # kit default

    parsed = json.loads((run_dir / "resolved-tokens.json").read_text())
    provenance = parsed["_layer_provenance"]
    # primary_accent came from kit defaults, NOT from brand (brand was skipped).
    assert provenance["palette.primary_accent"] == "kit_default"
    # No 'extends' key should appear in provenance.
    assert "extends" not in provenance
