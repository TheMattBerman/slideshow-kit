"""Format-aware structure lint for carousel scripts.

Validates: slot count ranges, per-slot word counts, close-action vocabulary
match. Emits Violation records reusing v0.6.1's voice_lint.Violation type.
"""

from __future__ import annotations

import os
import re
from typing import Optional

from .voice_lint import Violation
from .format_registry import VALID_CLOSE_ACTIONS, get_format
from .style_overrides import load_style_overrides, merge_word_count_override


CLOSE_VOCAB: dict[str, list[str]] = {
    "save": ["save", "bookmark", "screenshot", "come back to"],
    "share": ["share", "send", "send to", "tag", "dm this to", "forward"],
    "comment": ["comment", "drop", "tell me below", "reply", "type"],
    "soft": [],
}


def _word_count(text: str) -> int:
    """Count whitespace-separated tokens (close enough for word-count enforcement)."""
    return len(text.split())


def _load_brand_close_vocab(path: Optional[str]) -> dict[str, list[str]]:
    """Parse brand-voice.md '## Close vocabulary' section.

    Returns {action: [phrase, ...]} where keys are subset of CLOSE_VOCAB keys.
    Phrases are added to (not replacing) kit defaults at lookup time.
    """
    if path is None:
        return {}
    try:
        with open(path) as f:
            content = f.read()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return {}

    out: dict[str, list[str]] = {}
    in_section = False
    current_action: Optional[str] = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped.lower() == "## close vocabulary"
            current_action = None
            continue
        if not in_section:
            continue
        if stripped.startswith("### "):
            action = stripped[4:].strip().lower()
            if action in CLOSE_VOCAB:
                current_action = action
                out.setdefault(current_action, [])
            else:
                current_action = None
            continue
        if current_action is None:
            continue
        if stripped.startswith("- "):
            phrase = stripped[2:].strip().strip('"').strip("'")
            if phrase:
                out[current_action].append(phrase)
    return out


def _resolve_close_vocab(action: str, brand_extra: dict[str, list[str]]) -> list[str]:
    return list(CLOSE_VOCAB.get(action, [])) + brand_extra.get(action, [])


def _contains_close_phrase(body_lower: str, phrase: str) -> bool:
    if phrase.lower() == "send":
        return bool(re.search(r"\bsend\s+(this|it|to)\b", body_lower))
    return bool(re.search(r"\b" + re.escape(phrase.lower()) + r"\b", body_lower))


def _matched_close_action_groups(
    body_lower: str,
    brand_extra: dict[str, list[str]],
) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for action in ("save", "share", "comment"):
        action_matches = [
            phrase
            for phrase in _resolve_close_vocab(action, brand_extra)
            if _contains_close_phrase(body_lower, phrase)
        ]
        if action_matches:
            matches[action] = action_matches
    return matches


def _heading_role_token(heading_line: str) -> Optional[str]:
    if not heading_line.startswith("#"):
        return None
    stripped = heading_line.lstrip("#").strip()
    if not stripped:
        return None
    first = stripped.split()[0]
    cleaned = "".join(c for c in first if c.isalpha() or c == "_")
    cleaned = cleaned.rstrip("_")
    return cleaned.upper() if cleaned else None


def lint_script_structure(
    text: str,
    format_name: str,
    close_action: str,
    brand_voice_path: Optional[str] = None,
    style_dir: Optional[str] = None,
) -> list[Violation]:
    violations: list[Violation] = []

    style_overrides = load_style_overrides(style_dir) if style_dir else {}

    try:
        fmt = get_format(format_name)
    except ValueError:
        violations.append(
            Violation(
                severity="error",
                rule_id="format_unknown_format",
                line=1,
                column=1,
                snippet=format_name,
                message=f"format '{format_name}' is not defined in references/formats/",
            )
        )
        return violations

    if close_action not in VALID_CLOSE_ACTIONS:
        violations.append(
            Violation(
                severity="error",
                rule_id="format_unknown_close_action",
                line=1,
                column=1,
                snippet=close_action,
                message=(
                    f"close_action '{close_action}' not in "
                    f"{sorted(VALID_CLOSE_ACTIONS)}"
                ),
            )
        )
        return violations

    # Walk headings + bodies, mirroring script_parser logic but emitting
    # violations instead of raising.
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if line.startswith("#"):
            headings.append((i, line))

    slot_idx = 0
    consumed_in_slot = 0
    h_idx = 0
    parsed_slides: list[tuple[str, str, int]] = []  # (slot_role, body, line_num)

    while h_idx < len(headings) and slot_idx < len(fmt.slots):
        line_idx, heading = headings[h_idx]
        token = _heading_role_token(heading)
        slot = fmt.slots[slot_idx]

        if token in slot.aliases:
            next_line_idx = (
                headings[h_idx + 1][0] if h_idx + 1 < len(headings) else len(lines)
            )
            body = "\n".join(lines[line_idx + 1 : next_line_idx]).strip()
            parsed_slides.append((slot.role, body, line_idx + 1))
            consumed_in_slot += 1
            h_idx += 1

            if consumed_in_slot >= slot.count_max:
                slot_idx += 1
                consumed_in_slot = 0
                continue

            if h_idx < len(headings):
                next_token = _heading_role_token(headings[h_idx][1])
                if next_token not in slot.aliases:
                    if consumed_in_slot < slot.count_min:
                        violations.append(
                            Violation(
                                severity="error",
                                rule_id="format_missing_slot",
                                line=line_idx + 1,
                                column=1,
                                snippet=slot.role,
                                message=(
                                    f"slot {slot.role} requires at least "
                                    f"{slot.count_min}; got {consumed_in_slot}."
                                ),
                            )
                        )
                    slot_idx += 1
                    consumed_in_slot = 0
            else:
                if consumed_in_slot < slot.count_min:
                    violations.append(
                        Violation(
                            severity="error",
                            rule_id="format_missing_slot",
                            line=line_idx + 1,
                            column=1,
                            snippet=slot.role,
                            message=(
                                f"slot {slot.role} requires at least "
                                f"{slot.count_min}; got {consumed_in_slot}."
                            ),
                        )
                    )
                slot_idx += 1
                consumed_in_slot = 0
        else:
            # Token doesn't match current slot. If it matches the just-completed
            # (previous) slot's aliases, that slot is over-capped.
            prev_slot = fmt.slots[slot_idx - 1] if slot_idx > 0 else None
            if prev_slot is not None and token in prev_slot.aliases:
                violations.append(
                    Violation(
                        severity="error",
                        rule_id="format_too_many_slots",
                        line=line_idx + 1,
                        column=1,
                        snippet=prev_slot.role,
                        message=(
                            f"slot {prev_slot.role} allows at most "
                            f"{prev_slot.count_max}; got more."
                        ),
                    )
                )
                h_idx += 1
                continue
            # Otherwise advance if current-slot min satisfied, else flag unknown role.
            if consumed_in_slot >= slot.count_min:
                slot_idx += 1
                consumed_in_slot = 0
            else:
                violations.append(
                    Violation(
                        severity="error",
                        rule_id="format_unknown_role",
                        line=line_idx + 1,
                        column=1,
                        snippet=heading.strip(),
                        message=(
                            f"heading '{heading.strip()}' (token '{token}') does not "
                            f"match slot {slot.role} aliases {slot.aliases}."
                        ),
                    )
                )
                h_idx += 1  # skip unmatched heading to keep walking

    # Remaining unmatched headings: too many for last slot or unknown.
    while h_idx < len(headings):
        line_idx, heading = headings[h_idx]
        token = _heading_role_token(heading)
        last_slot = fmt.slots[-1] if fmt.slots else None
        if last_slot and token in last_slot.aliases:
            violations.append(
                Violation(
                    severity="error",
                    rule_id="format_too_many_slots",
                    line=line_idx + 1,
                    column=1,
                    snippet=last_slot.role,
                    message=(
                        f"slot {last_slot.role} allows at most {last_slot.count_max}; "
                        f"got more."
                    ),
                )
            )
        else:
            violations.append(
                Violation(
                    severity="error",
                    rule_id="format_unknown_role",
                    line=line_idx + 1,
                    column=1,
                    snippet=heading.strip(),
                    message=f"heading '{heading.strip()}' did not match any remaining slot.",
                )
            )
        h_idx += 1

    # Remaining required slots not consumed.
    while slot_idx < len(fmt.slots):
        slot = fmt.slots[slot_idx]
        if consumed_in_slot < slot.count_min:
            violations.append(
                Violation(
                    severity="error",
                    rule_id="format_missing_slot",
                    line=1,
                    column=1,
                    snippet=slot.role,
                    message=(
                        f"slot {slot.role} requires at least {slot.count_min}; "
                        f"got {consumed_in_slot}."
                    ),
                )
            )
        slot_idx += 1
        consumed_in_slot = 0

    # Word-count checks per parsed slide.
    slot_by_role = {s.role: s for s in fmt.slots}
    for role, body, line_num in parsed_slides:
        slot = slot_by_role.get(role)
        if slot is None:
            continue
        wc = _word_count(body)
        format_range = (slot.word_count_min, slot.word_count_max)
        override = style_overrides.get(role)
        wc_min, wc_max = merge_word_count_override(format_range, override)
        override_suffix = ""
        if style_dir and role in style_overrides:
            override_suffix = (
                f" (override from {os.path.join(style_dir, 'style.yaml')})"
            )
        if wc < wc_min:
            violations.append(
                Violation(
                    severity="error",
                    rule_id="format_word_count_low",
                    line=line_num,
                    column=1,
                    snippet=f"{role}: {wc} words",
                    message=(
                        f"slot {role} body is {wc} words; min is "
                        f"{wc_min}.{override_suffix}"
                    ),
                )
            )
        if wc > wc_max:
            violations.append(
                Violation(
                    severity="error",
                    rule_id="format_word_count_high",
                    line=line_num,
                    column=1,
                    snippet=f"{role}: {wc} words",
                    message=(
                        f"slot {role} body is {wc} words; max is "
                        f"{wc_max}.{override_suffix}"
                    ),
                )
            )

    # Close vocab checks.
    if parsed_slides:
        last_role, last_body, last_line = parsed_slides[-1]
        # Only check vocab if the last parsed slide is actually the format's final slot.
        # If CTA is missing, format_missing_slot already fires; skip vocab check.
        if last_role == fmt.slots[-1].role:
            brand_extra = _load_brand_close_vocab(brand_voice_path)
            body_lower = last_body.lower()
            matched_groups = _matched_close_action_groups(body_lower, brand_extra)
            if len(matched_groups) > 1:
                actions = sorted(matched_groups)
                violations.append(
                    Violation(
                        severity="error",
                        rule_id="format_close_multiple_actions",
                        line=last_line,
                        column=1,
                        snippet=last_body[:60],
                        message=(
                            "close slide must contain exactly one primary action "
                            f"group; found {actions}. Do not combine save, share, "
                            "and comment calls to action."
                        ),
                    )
                )
            if close_action != "soft":
                vocab = _resolve_close_vocab(close_action, brand_extra)
                has_requested_action = any(
                    _contains_close_phrase(body_lower, v) for v in vocab
                )
                if not has_requested_action:
                    violations.append(
                        Violation(
                            severity="error",
                            rule_id="format_close_missing_action",
                            line=last_line,
                            column=1,
                            snippet=last_body[:60],
                            message=(
                                f"close slide must contain {close_action} vocabulary "
                                f"(one of: {vocab[:6]}{'...' if len(vocab) > 6 else ''}). "
                                "Use close_action: soft if the close is intentionally observational."
                            ),
                        )
                    )

    violations.sort(key=lambda v: (v.line, v.column))
    return violations
