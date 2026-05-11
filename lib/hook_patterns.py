"""Six-pattern hook generation primitive for concept-generator.

Each pattern has a description, exemplars (lifted from Matt's published work),
and a 'when_to_use' guide. The host agent references these via the
concept_generation prompt to produce hook variety per concept.
"""

from __future__ import annotations

from typing import TypedDict


class _PatternEntry(TypedDict):
    description: str
    exemplars: list[str]
    when_to_use: str


HOOK_PATTERNS: dict[str, _PatternEntry] = {
    "single_claim": {
        "description": "One emotional pull, one complete idea, demands the next line.",
        "exemplars": [
            "i replaced my $11k product photographer with one prompt.",
            "gpt image 2 just killed my $11k product photographer.",
            "i run my meta ads with @openclaw for $0/month.",
        ],
        "when_to_use": "Tactical receipts, dollar amounts, replacement-of-X claims.",
    },
    "question": {
        "description": "Curiosity gap that demands resolution.",
        "exemplars": [
            "what does claude know about your brand that you don't?",
            "why does the same model produce $11k output for one operator and garbage for another?",
        ],
        "when_to_use": "ICP education, framework introduction, contrarian setup.",
    },
    "scene": {
        "description": "Dated, sensory, specific opening moment.",
        "exemplars": [
            "tuesday 2pm. the agency invoice line was gone.",
            "10 minutes scrolling. 12 carousels. 4 of them used identical structure.",
        ],
        "when_to_use": "Personal anecdote, transformation, before/after story.",
    },
    "dialogue": {
        "description": "Quoted line that becomes the load-bearing element of the post.",
        "exemplars": [
            'a $15M ARR founder told me: "ai carousels all look the same."',
            'lemkin said it on his last podcast: "the agency model is dead."',
        ],
        "when_to_use": "Receipt + context, counter-narrative, borrowed authority.",
    },
    "contrast": {
        "description": "Two things that should not both be true; paradox surface.",
        "exemplars": [
            "we doubled output. we cut headcount in half.",
            "the model that designs them is invisible. the carousels it designs are obvious.",
        ],
        "when_to_use": "Process reveal, before/after, anatomy breakdowns.",
    },
    "observation": {
        "description": "Insider point at something the reader will see in their own world.",
        "exemplars": [
            "scroll your feed. count the carousels with exactly 6 slides.",
            "most founders are still hiring marketing teams when they could be building agents.",
        ],
        "when_to_use": "Numbered diagnostic, counter-narrative, ICP education.",
    },
}


def get_pattern(name: str) -> _PatternEntry:
    """Return the registry entry for a named pattern. Raises KeyError if unknown."""
    return HOOK_PATTERNS[name]


def list_patterns() -> list[str]:
    """Return pattern names in sorted order."""
    return sorted(HOOK_PATTERNS.keys())
