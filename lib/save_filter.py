"""Save-worthiness filter for body slides.

Heuristic gate (specific numbers, dates, tactical-aside markers, quotes,
named-framework markers) plus optional LLM fallback callback.

Adapts to effective word-cap:
- Tight slots (effective_word_cap_max <= 12): one marker is sufficient.
- Standard slots (effective_word_cap_max >= 13): need markers from >= 2
  category buckets (number, date, tactical_aside, quote, named_framework).
"""

from __future__ import annotations

import json as _json
import re
import ssl
import sys
from typing import Callable, Optional
from urllib.error import HTTPError, URLError

from .voice_lint import Violation


_KNOWN_LLM_FAILURES = (
    HTTPError,
    URLError,
    ssl.SSLError,
    _json.JSONDecodeError,
    TimeoutError,
    ConnectionError,
)


HOOK_ROLES = {"HOOK", "COVER"}
CTA_ROLES = {"CTA", "CLOSE", "ACTION"}

TIGHT_SLOT_WORD_CAP_MAX = 12
SNIPPET_TRUNCATION_LENGTH = 60

# Backward-compat alias.
TIGHT_SLOT_THRESHOLD = TIGHT_SLOT_WORD_CAP_MAX


_RE_NUMBER = re.compile(r"\b\d+(?:\.\d+)?(?:k|m|x|%)(?=\W|$)", re.IGNORECASE)
_RE_NUMBER_DOLLAR = re.compile(r"\$\d+(?:\.\d+)?(?:k|m)?\b", re.IGNORECASE)
_RE_DATE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_RE_DATE_MONTH = re.compile(
    r"\b(?:january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
_RE_RELATIVE_DATE = re.compile(
    r"\blast (?:week|month|year|night|tuesday|november|quarter)\b",
    re.IGNORECASE,
)
_RE_TACTICAL_ASIDE = re.compile(
    r"\b(?:tip|fwiw|tbh|real talk|here'?s the move|here'?s the play|pro tip)\s*:",
    re.IGNORECASE,
)
_RE_QUOTE = re.compile(r'(?:"[^"\n]{2,}"|“[^”“\n]{2,}”|"[^"”\n]{2,}”)')
_RE_NAMED_FRAMEWORK = re.compile(
    r"\b(?:i call this|the\s+\d+(?:-|\s)?(?:tells?|rules?|moves?|steps?))\b",
    re.IGNORECASE,
)


def _detect_categories(body: str) -> set[str]:
    """Return the set of marker categories detected in body.

    Categories: number, date, tactical_aside, quote, named_framework.
    """
    cats: set[str] = set()
    if _RE_NUMBER_DOLLAR.search(body) or _RE_NUMBER.search(body):
        cats.add("number")
    if (
        _RE_DATE_ISO.search(body)
        or _RE_DATE_MONTH.search(body)
        or _RE_RELATIVE_DATE.search(body)
    ):
        cats.add("date")
    if _RE_TACTICAL_ASIDE.search(body):
        cats.add("tactical_aside")
    if _RE_QUOTE.search(body):
        cats.add("quote")
    if _RE_NAMED_FRAMEWORK.search(body):
        cats.add("named_framework")
    return cats


def check_save_worthiness(
    slide_role: str,
    slide_body: str,
    *,
    use_llm_fallback: bool = True,
    llm_judge_callback: Optional[Callable[[str], bool]] = None,
    effective_word_cap_max: int = TIGHT_SLOT_WORD_CAP_MAX,
) -> list[Violation]:
    """Return [] if slide is save-worthy; [Violation] if not.

    HOOK and CTA slots are exempt (different rules per format-lint).

    effective_word_cap_max controls the heuristic threshold:
    - <= 12 (tight): one marker category is sufficient.
    - >= 13 (standard): markers from >= 2 categories required.
    Default is 12 (tight) to preserve backward-compat with callers that
    don't pass the parameter.
    """
    role = slide_role.upper()
    if role in HOOK_ROLES or role in CTA_ROLES:
        return []

    cats = _detect_categories(slide_body)

    if effective_word_cap_max <= TIGHT_SLOT_WORD_CAP_MAX:
        if len(cats) >= 1:
            return []
        threshold_desc = "tight slot needs at least 1 save-worthy marker"
    else:
        if len(cats) >= 2:
            return []
        threshold_desc = (
            "standard slot needs save-worthy markers from at least 2 categories"
        )

    if use_llm_fallback and llm_judge_callback is not None:
        try:
            if llm_judge_callback(slide_body):
                return []
        except _KNOWN_LLM_FAILURES as e:
            print(
                f"[WARN] save_filter: llm_judge_callback failed ({type(e).__name__}: {e}); "
                f"falling through to heuristic verdict.",
                file=sys.stderr,
            )
        except Exception as e:
            # Third-party callback boundary: callback bugs should not bypass
            # the deterministic heuristic verdict for the slide.
            print(
                f"[WARN] save_filter: llm_judge_callback raised unexpected {type(e).__name__}: {e}; "
                f"check the callback implementation. Falling through to heuristic.",
                file=sys.stderr,
            )

    snippet = slide_body[:SNIPPET_TRUNCATION_LENGTH]
    return [
        Violation(
            severity="error",
            rule_id="save_filter_thin_slide",
            line=1,
            column=1,
            snippet=snippet,
            message=(
                f"slot {role} body has insufficient save-worthy specifics "
                f"(detected categories: {sorted(cats) or 'none'}; "
                f"effective_word_cap_max={effective_word_cap_max}; "
                f"{threshold_desc}). "
                "Add a specific number, date, named framework, quote, or "
                "tactical aside, or pass --no-save-filter to bypass."
            ),
        )
    ]
