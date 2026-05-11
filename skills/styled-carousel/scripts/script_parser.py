"""Format-aware script parser for styled-carousel.

Reads optional YAML frontmatter (format, close_action), loads the format
definition from references/formats/, walks `# HEADING` lines matching slot
aliases, and returns ParsedScript with structured slides.
"""

from __future__ import annotations

import os
import sys
from typing import NamedTuple, Optional

import yaml

# Make the kit root importable so we can use lib/.
_HERE = os.path.dirname(os.path.abspath(__file__))
_KIT_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
if _KIT_ROOT not in sys.path:
    sys.path.insert(0, _KIT_ROOT)

from lib.format_registry import FormatDef, VALID_CLOSE_ACTIONS, get_format


class Slide(NamedTuple):
    slot_role: str
    heading: str
    body: str


class ParsedScript(NamedTuple):
    format_name: str
    close_action: str
    slides: list[Slide]


def _split_frontmatter(text: str) -> tuple[Optional[dict], str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict_or_None, body_str)."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text

    fm_lines: list[str] = []
    closed = False
    body_start = 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closed = True
            body_start = i + 1
            break
        fm_lines.append(lines[i])

    if not closed:
        raise ValueError("frontmatter started with --- but never closed")

    try:
        fm = yaml.safe_load("".join(fm_lines)) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"frontmatter YAML malformed: {e}") from e

    if not isinstance(fm, dict):
        raise ValueError("frontmatter must be a YAML mapping")

    body = "".join(lines[body_start:])
    return fm, body


def _heading_role_token(heading_line: str) -> Optional[str]:
    """Extract the role token from a heading line.

    `# TELL #1: it has 6 slides` -> 'TELL'
    `# HOOK` -> 'HOOK'
    `# STEP_1` -> 'STEP'
    """
    if not heading_line.startswith("#"):
        return None
    # Strip leading hashes and whitespace.
    stripped = heading_line.lstrip("#").strip()
    if not stripped:
        return None
    # Take the first token (uppercase ASCII run).
    first = stripped.split()[0]
    # Allow underscore-joined (THE_QUOTE) and uppercase.
    cleaned = "".join(c for c in first if c.isalpha() or c == "_")
    # Strip trailing underscores left by digit suffixes e.g. STEP_1 -> STEP_.
    cleaned = cleaned.rstrip("_")
    return cleaned.upper() if cleaned else None


def _walk_body(body: str, fmt: FormatDef) -> list[Slide]:
    """Walk body lines, matching headings to slot aliases in order."""
    lines = body.splitlines()
    headings: list[tuple[int, str]] = []  # (line_idx, heading_line)
    for i, line in enumerate(lines):
        if line.startswith("#"):
            headings.append((i, line))

    slides: list[Slide] = []
    slot_idx = 0
    consumed_in_slot = 0
    h_idx = 0

    while h_idx < len(headings) and slot_idx < len(fmt.slots):
        line_idx, heading = headings[h_idx]
        token = _heading_role_token(heading)
        slot = fmt.slots[slot_idx]

        if token in slot.aliases:
            # Matches current slot: consume.
            next_line_idx = headings[h_idx + 1][0] if h_idx + 1 < len(headings) else len(lines)
            body_text = "\n".join(lines[line_idx + 1 : next_line_idx]).strip()
            slides.append(Slide(slot_role=slot.role, heading=heading.strip(), body=body_text))
            consumed_in_slot += 1
            h_idx += 1

            # Advance slot if we hit count_max or the next heading doesn't match this slot.
            if consumed_in_slot >= slot.count_max:
                slot_idx += 1
                consumed_in_slot = 0
                continue
            # Peek the next heading; if it doesn't match this slot's aliases, advance the slot.
            if h_idx < len(headings):
                next_token = _heading_role_token(headings[h_idx][1])
                if next_token not in slot.aliases:
                    if consumed_in_slot < slot.count_min:
                        raise ValueError(
                            f"format '{fmt.name}': slot {slot.role} requires at least "
                            f"{slot.count_min} entries; got {consumed_in_slot} "
                            f"(valid aliases: {slot.aliases})."
                        )
                    slot_idx += 1
                    consumed_in_slot = 0
            else:
                if consumed_in_slot < slot.count_min:
                    raise ValueError(
                        f"format '{fmt.name}': slot {slot.role} requires at least "
                        f"{slot.count_min} entries; got {consumed_in_slot} "
                        f"(valid aliases: {slot.aliases})."
                    )
                slot_idx += 1
                consumed_in_slot = 0
        else:
            # Doesn't match current slot: try advancing the slot if we satisfied the min.
            if consumed_in_slot >= slot.count_min:
                slot_idx += 1
                consumed_in_slot = 0
                continue
            raise ValueError(
                f"format '{fmt.name}': heading '{heading.strip()}' does not match slot "
                f"{slot.role} (aliases: {slot.aliases}). Got token '{token}'."
            )

    # Validate any remaining slots have count_min == 0 OR have been satisfied.
    while slot_idx < len(fmt.slots):
        slot = fmt.slots[slot_idx]
        if consumed_in_slot < slot.count_min:
            raise ValueError(
                f"format '{fmt.name}': slot {slot.role} requires at least "
                f"{slot.count_min} entries; got {consumed_in_slot} "
                f"(valid aliases: {slot.aliases})."
            )
        slot_idx += 1
        consumed_in_slot = 0

    # If headings remain, they're unmatched.
    if h_idx < len(headings):
        unmatched = headings[h_idx][1].strip()
        raise ValueError(f"format '{fmt.name}': extra heading '{unmatched}' did not match any slot")

    return slides


def parse_script(path: str) -> ParsedScript:
    """Parse a script file with optional YAML frontmatter into a ParsedScript."""
    with open(path) as f:
        text = f.read()

    fm, body = _split_frontmatter(text)
    fm = fm or {}

    format_name = fm.get("format", "narrative")
    fmt = get_format(format_name)  # raises ValueError on unknown

    close_action = fm.get("close_action", fmt.default_close_action)
    if close_action not in VALID_CLOSE_ACTIONS:
        raise ValueError(
            f"close_action '{close_action}' not in {sorted(VALID_CLOSE_ACTIONS)}"
        )

    slides = _walk_body(body, fmt)

    return ParsedScript(
        format_name=format_name,
        close_action=close_action,
        slides=slides,
    )
