"""Load and validate carousel format definitions from references/formats/."""

from __future__ import annotations

import os
import yaml
from typing import NamedTuple


class Slot(NamedTuple):
    role: str
    count_min: int
    count_max: int
    word_count_min: int
    word_count_max: int
    aliases: list[str]


class FormatDef(NamedTuple):
    name: str
    description: str
    default_close_action: str
    slots: list[Slot]


VALID_CLOSE_ACTIONS = {"save", "share", "comment", "soft"}


def _formats_dir() -> str:
    """Locate references/formats/ relative to the kit root."""
    here = os.path.dirname(os.path.abspath(__file__))
    kit_root = os.path.dirname(here)
    return os.path.join(kit_root, "references", "formats")


def _validate_slot(raw: dict, format_name: str) -> Slot:
    role = raw.get("role")
    if not role or not isinstance(role, str):
        raise ValueError(f"format '{format_name}': slot missing 'role'")
    role = role.upper()

    if "count" in raw:
        count_min = count_max = int(raw["count"])
    elif "count_range" in raw:
        rng = raw["count_range"]
        if not (isinstance(rng, list) and len(rng) == 2):
            raise ValueError(f"format '{format_name}': slot {role}: count_range must be [min, max]")
        count_min, count_max = int(rng[0]), int(rng[1])
        if count_min > count_max:
            raise ValueError(f"format '{format_name}': slot {role}: count_min > count_max")
    else:
        raise ValueError(f"format '{format_name}': slot {role}: needs count or count_range")

    word_range = raw.get("word_count_range")
    if not (isinstance(word_range, list) and len(word_range) == 2):
        raise ValueError(f"format '{format_name}': slot {role}: word_count_range required")
    word_min, word_max = int(word_range[0]), int(word_range[1])
    if word_min > word_max:
        raise ValueError(f"format '{format_name}': slot {role}: word_count_min > word_count_max")

    aliases_raw = raw.get("aliases", [role])
    if not aliases_raw:
        raise ValueError(f"format '{format_name}': slot {role}: aliases must be non-empty")
    aliases = [a.upper() for a in aliases_raw]

    return Slot(
        role=role,
        count_min=count_min,
        count_max=count_max,
        word_count_min=word_min,
        word_count_max=word_max,
        aliases=aliases,
    )


def get_format(name: str) -> FormatDef:
    """Load and parse references/formats/<name>.yaml."""
    path = os.path.join(_formats_dir(), f"{name}.yaml")
    if not os.path.isfile(path):
        raise ValueError(f"unknown format '{name}': no file at {path}")
    with open(path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"format '{name}': malformed YAML: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"format '{name}': top-level must be a mapping")

    fmt_name = data.get("name")
    if fmt_name != name:
        raise ValueError(f"format '{name}': name field '{fmt_name}' must match filename")

    description = str(data.get("description", "")).strip()
    close_action = data.get("default_close_action", "save")
    if close_action not in VALID_CLOSE_ACTIONS:
        raise ValueError(
            f"format '{name}': default_close_action '{close_action}' not in {sorted(VALID_CLOSE_ACTIONS)}"
        )

    slots_raw = data.get("slots")
    if not isinstance(slots_raw, list) or not slots_raw:
        raise ValueError(f"format '{name}': slots must be a non-empty list")
    slots: list[Slot] = []
    for i, s in enumerate(slots_raw):
        if not isinstance(s, dict):
            raise ValueError(
                f"format '{name}': slot[{i}] must be a mapping, got {type(s).__name__}"
            )
        slots.append(_validate_slot(s, name))

    return FormatDef(
        name=name,
        description=description,
        default_close_action=close_action,
        slots=slots,
    )


def list_formats() -> list[str]:
    """Enumerate format names from references/formats/*.yaml."""
    d = _formats_dir()
    if not os.path.isdir(d):
        return []
    out = []
    for fname in os.listdir(d):
        if fname.endswith(".yaml"):
            out.append(fname[:-5])
    return sorted(out)
