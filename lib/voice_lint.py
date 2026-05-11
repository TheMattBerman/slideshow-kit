"""Voice lint: detect em-dashes, AI-tell patterns, banned words.

Three call sites use this:
  1. Pre-render hook in skills/styled-carousel/scripts/generate_styled_carousel.py
  2. Standalone CLI: scripts/lint_script.sh
  3. doctor.sh per-brand brand-voice.md scan
"""

from __future__ import annotations

import re
from typing import NamedTuple, Optional


class Violation(NamedTuple):
    severity: str  # always "error" in v0.6.1
    rule_id: str
    line: int
    column: int
    snippet: str
    message: str


EM_DASH = "—"  # the literal em-dash character

PATTERN_RULES = [
    (
        "pattern_not_x_its_y",
        re.compile(r"\bnot\b[^.\n]{1,40}\bit'?s\b", re.IGNORECASE),
        "'not X, it's Y' is a load-bearing AI tell. Replace with a tactical, observational, or specific line.",
    ),
    (
        "pattern_not_just",
        re.compile(r"\bnot just\b[^.\n]{1,40}\b(but|it'?s)\b", re.IGNORECASE),
        "'not just X, but Y' is an AI rhythm. Replace with an asymmetric construction.",
    ),
    (
        "pattern_dont_just",
        re.compile(r"\bdon'?t just\b[^.\n]{1,40}[.\n]", re.IGNORECASE),
        "'don't just X. Y.' is an AI rhythm. Go tactical or specific instead.",
    ),
    (
        "pattern_truth_is",
        re.compile(
            r"^\s*(the truth is|here'?s the thing|and that'?s the whole point)\b",
            re.IGNORECASE,
        ),
        "Aphoristic openers read as AI. Open with something specific, dated, or observational.",
    ),
]


BANNED_WORDS_ENG_JARGON = [
    "deprecated",
    "refactor",
    "parameterize",
    "leverage",
    "optimize",
    "iterate",
    "docstring",
    "legacy",
]

_BANNED_WORD_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in BANNED_WORDS_ENG_JARGON) + r")\b",
    re.IGNORECASE,
)


def _scan_pattern_rules(line: str, line_num: int) -> list[Violation]:
    out: list[Violation] = []
    for rule_id, regex, message in PATTERN_RULES:
        for match in regex.finditer(line):
            out.append(
                Violation(
                    severity="error",
                    rule_id=rule_id,
                    line=line_num,
                    column=match.start() + 1,
                    snippet=match.group(0),
                    message=message,
                )
            )
    return out


def _load_brand_avoid_section(path: Optional[str]) -> list[tuple[str, re.Pattern]]:
    """Parse the `## Avoid` section of a brand-voice.md.

    Returns a list of (rule_id, compiled_regex). Three line forms supported:
      - "literal phrase"     -> word-boundary, case-insensitive
      - regex: <pattern>     -> compiled as-is
      - pattern: <name>      -> v0.6.1: silently ignored (named-pattern engine deferred per spec section 7 question 2)
    """
    if path is None:
        return []
    try:
        with open(path) as f:
            content = f.read()
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        return []

    rules: list[tuple[str, re.Pattern]] = []
    in_avoid = False
    counter = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_avoid = stripped.lower() == "## avoid"
            continue
        if not in_avoid:
            continue
        if not stripped.startswith("- "):
            continue
        body = stripped[2:].strip()
        if "#" in body:
            body = body.split("#", 1)[0].rstrip()

        if body.startswith("regex:"):
            try:
                pat = re.compile(body[len("regex:"):].strip(), re.IGNORECASE)
            except re.error:
                continue
            counter += 1
            rules.append((f"brand_avoid_regex_{counter}", pat))
        elif body.startswith("pattern:"):
            continue
        else:
            phrase = body.strip().strip('"').strip("'")
            if not phrase:
                continue
            try:
                pat = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
            except re.error:
                continue
            counter += 1
            rules.append((f"brand_avoid_literal_{counter}", pat))
    return rules


def lint_text(text: str, brand_voice_path: Optional[str] = None) -> list[Violation]:
    """Lint a body of text against kit-default + brand-declared rules.

    Returns empty list when clean. Severity is always 'error' in v0.6.1.
    Violations are returned in (line, column) order.
    """
    brand_rules = _load_brand_avoid_section(brand_voice_path)
    violations: list[Violation] = []
    for line_num, line in enumerate(text.splitlines(), start=1):
        # Em-dash scan.
        col = 0
        while True:
            idx = line.find(EM_DASH, col)
            if idx == -1:
                break
            violations.append(
                Violation(
                    severity="error",
                    rule_id="em_dash",
                    line=line_num,
                    column=idx + 1,
                    snippet=line[max(0, idx - 10) : idx + 11],
                    message="em-dash is banned (AI tell). Use period, comma, or colon.",
                )
            )
            col = idx + 1
        # Pattern-rule scan.
        violations.extend(_scan_pattern_rules(line, line_num))
        # Banned-word scan.
        for match in _BANNED_WORD_RE.finditer(line):
            violations.append(
                Violation(
                    severity="error",
                    rule_id="banned_word_eng_jargon",
                    line=line_num,
                    column=match.start() + 1,
                    snippet=match.group(0),
                    message=(
                        f"'{match.group(0)}' is engineering jargon. "
                        "Replace with the plain-English equivalent."
                    ),
                )
            )
        # Brand-rule scan.
        for rule_id, regex in brand_rules:
            for match in regex.finditer(line):
                violations.append(
                    Violation(
                        severity="error",
                        rule_id=rule_id,
                        line=line_num,
                        column=match.start() + 1,
                        snippet=match.group(0),
                        message=f"brand rule '{rule_id}' matched: {match.group(0)!r}",
                    )
                )
    violations.sort(key=lambda v: (v.line, v.column))
    return violations
