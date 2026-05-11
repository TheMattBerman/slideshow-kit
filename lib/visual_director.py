"""LLM-driven per-slide scene direction for character-driven carousels.

Reads the parsed script + visual-hook + concept-arc + brand-design and produces
ONE scene brief per slide that serves the slide's beat, varies meaningfully
across the carousel, and stays in character.

Public surface:
    SceneBrief, SceneDirection: NamedTuples for the per-slide output.
    CHARACTER_DRIVEN_TREATMENTS: set of image_treatment strings that opt in.
    SCENE_DIRECTION_SOURCES: ("stage_3", "renderer_fallback").
    direct_scenes(...): main entry point.
    scene_direction_to_markdown / scene_direction_from_markdown: serialization.
"""

from __future__ import annotations

import json
import os
import ssl
import sys
from typing import NamedTuple, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

try:
    import certifi
    HAS_CERTIFI = True
except ImportError:
    certifi = None  # type: ignore[assignment]
    HAS_CERTIFI = False


CHARACTER_DRIVEN_TREATMENTS = {"iphone_candid"}

DIRECT_SCENES_PROMPT_CAP = 2000
DIRECT_SCENES_CONTEXT_FIELD_CAP = 300

API_URL = "https://api.openai.com/v1/chat/completions"


class SceneBrief(NamedTuple):
    role: str
    scene_brief: str
    tone: str


class SceneDirection(NamedTuple):
    slides: list[SceneBrief]
    source: str  # "stage_3" | "renderer_fallback"


SCENE_DIRECTION_SOURCES = ("stage_3", "renderer_fallback")
_VALID_SCENE_SOURCES = set(SCENE_DIRECTION_SOURCES)


def scene_direction_to_markdown(sd: SceneDirection) -> str:
    """Serialize SceneDirection to scene-direction.md format."""
    if sd.source not in _VALID_SCENE_SOURCES:
        raise ValueError(
            f"scene_direction_to_markdown: source must be one of "
            f"{sorted(_VALID_SCENE_SOURCES)}, got: {sd.source!r}"
        )
    lines = [f"# Scene direction (source: {sd.source})", ""]
    for i, sb in enumerate(sd.slides, start=1):
        lines.extend([
            f"## Slide {i} ({sb.role})",
            f"**Tone:** {sb.tone}",
            f"**Scene:** {sb.scene_brief}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def scene_direction_from_markdown(md: str) -> SceneDirection:
    """Parse scene-direction.md back into SceneDirection."""
    import re
    src_match = re.search(r"source:\s*(\w+)", md)
    if not src_match:
        raise ValueError("scene-direction.md missing source header")
    source = src_match.group(1)
    if source not in _VALID_SCENE_SOURCES:
        raise ValueError(
            f"scene-direction.md source {source!r} not in "
            f"{sorted(_VALID_SCENE_SOURCES)}"
        )
    slide_re = re.compile(
        r"^##\s+Slide\s+\d+\s+\(([^)]+)\)\s*\n"
        r"\*\*Tone:\*\*\s*(.+?)\s*\n"
        r"\*\*Scene:\*\*\s*(.+?)\s*$",
        re.MULTILINE,
    )
    slides = [
        SceneBrief(role=m.group(1).strip(), tone=m.group(2).strip(), scene_brief=m.group(3).strip())
        for m in slide_re.finditer(md)
    ]
    return SceneDirection(slides=slides, source=source)


def _is_ssl_cert_error(err: BaseException) -> bool:
    if isinstance(err, URLError):
        reason = getattr(err, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return True
        if isinstance(reason, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(reason):
            return True
    if isinstance(err, ssl.SSLCertVerificationError):
        return True
    if isinstance(err, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(err):
        return True
    return False


def _open_with_cert_fallback(req, timeout):
    """Open a urllib request; on SSL cert verify error, retry once with certifi."""
    try:
        return urlopen(req, timeout=timeout)
    except (URLError, ssl.SSLError) as e:
        if not _is_ssl_cert_error(e):
            raise
        if not HAS_CERTIFI:
            print(
                "[FAIL] SSL certificate verification failed and certifi is not "
                "installed. Install certifi (pip install certifi) to enable "
                "automatic SSL fallback.",
                file=sys.stderr,
            )
            raise
        print(
            "[INFO] SSL verify failed against system bundle; retrying with certifi.",
            file=sys.stderr,
        )
        assert certifi is not None
        ctx = ssl.create_default_context(cafile=certifi.where())
        return urlopen(req, timeout=timeout, context=ctx)


def _normalize_slide(s) -> tuple[str, str, str]:
    """Accept (slot_role, body, heading) tuple or Slide-like object; return tuple."""
    if isinstance(s, tuple) and len(s) >= 2:
        slot_role = s[0]
        body = s[1]
        heading = s[2] if len(s) >= 3 else ""
        return slot_role, body, heading
    # NamedTuple / object with attributes.
    slot_role = getattr(s, "slot_role", "")
    body = getattr(s, "body", "")
    heading = getattr(s, "heading", "")
    return slot_role, body, heading


def _parse_response_content(
    content: str,
    parsed_slides,
) -> list[dict]:
    """Parse the model's response content into a list of slide-visual dicts.

    Each dict has keys: slide_idx (int), slot_role (str), visual (str),
    rationale (str).

    Raises ValueError on JSON parse failure or schema mismatch.
    """
    # Some models wrap JSON in markdown fences; strip them.
    stripped = content.strip()
    if stripped.startswith("```"):
        # Drop the first line (``` or ```json) and the trailing ```.
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"visual director: response was not valid JSON ({e}). Raw: {content!r}"
        ) from e

    if not isinstance(data, list):
        raise ValueError(
            f"visual director: expected JSON list, got {type(data).__name__}. "
            f"Raw: {content!r}"
        )

    out: list[dict] = []
    seen_indices: set[int] = set()
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError(
                f"visual director: entry is not an object: {entry!r}"
            )
        idx = entry.get("slide_idx")
        visual = entry.get("visual")
        rationale = entry.get("rationale", "")
        tone = entry.get("tone", "neutral")
        if not isinstance(idx, int) or not isinstance(visual, str):
            raise ValueError(
                f"visual director: malformed entry (slide_idx must be int, "
                f"visual must be str): {entry!r}"
            )
        if idx < 0 or idx >= len(parsed_slides):
            raise ValueError(
                f"visual director: slide_idx {idx} out of range for "
                f"{len(parsed_slides)} slides"
            )
        if idx in seen_indices:
            raise ValueError(f"visual director: duplicate slide_idx {idx}")
        seen_indices.add(idx)
        if not isinstance(tone, str) or len(tone) > 20:
            tone = "neutral"
        # Look up slot_role from input.
        slot_role = ""
        if 0 <= idx < len(parsed_slides):
            slot_role, _, _ = _normalize_slide(parsed_slides[idx])
        out.append({
            "slide_idx": idx,
            "slot_role": slot_role,
            "visual": visual,
            "tone": tone,
            "rationale": rationale if isinstance(rationale, str) else "",
        })
    expected_indices = set(range(len(parsed_slides)))
    if seen_indices != expected_indices:
        missing = sorted(expected_indices - seen_indices)
        extra = sorted(seen_indices - expected_indices)
        raise ValueError(
            f"visual director: response must include exactly one entry per slide "
            f"(missing={missing}, extra={extra})"
        )
    out.sort(key=lambda entry: entry["slide_idx"])
    return out


def _call_openai(
    system_msg: str,
    user_msg: str,
    api_key: str,
    model: str,
) -> str:
    """POST to chat/completions, return the message content string."""
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.7,
    }).encode("utf-8")

    req = Request(
        API_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with _open_with_cert_fallback(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        raise ValueError(
            f"visual director: OpenAI HTTPError {e.code}: {e.reason}"
        ) from e

    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(
            f"visual director: unexpected response shape: {payload!r}"
        ) from e



DIRECT_SCENES_SYSTEM_PROMPT = (
    "You are a visual director for short-form social carousels. Read the "
    "carousel script and produce ONE scene brief per slide that serves the "
    "slide's beat, varies meaningfully across the carousel, and stays in "
    "character.\n\n"
    "Constraints:\n"
    "- Same person, same wardrobe across slides. Vary pose, expression, "
    "scene, lighting, crop based on what the slide says.\n"
    "- Each scene_brief is 25-45 words. Specific. No abstractions.\n"
    "- Output strict JSON: list of {\"slide_idx\": <int>, \"visual\": <str>, "
    "\"tone\": <str>, \"rationale\": <one sentence>}. slide_idx is 0-indexed.\n"
    "- Each entry includes a \"tone\" field: one short adjective phrase "
    "(<=20 chars) describing the scene's mood (e.g., \"observational\", "
    "\"punchy\", \"exhausted-but-amused\").\n"
    "- When a visual_hook is given, every scene must thread its visual "
    "through-line (location, time of day, prop, mood).\n"
    "- For a CTA slide, match the close action with one visual cue: save uses "
    "a bookmark or book cue, share uses an arrow, send, or DM cue, comment "
    "uses a bubble or typing cue, and soft uses no UI cue with a facial close."
)


def _build_direct_scenes_user_message(
    parsed_slides,
    visual_hook: Optional[str],
    concept_arc: Optional[str],
    brand_design: str,
    character_profile: Optional[str],
) -> str:
    """Compose the direct_scenes user message with a hard 2000-char cap."""
    slide_lines = []
    for idx, s in enumerate(parsed_slides):
        slot_role, body, _ = _normalize_slide(s)
        slide_lines.append(f"slide {idx} ({slot_role}): {body.strip()}")
    slides_block = "\n".join(slide_lines)

    parts: list[str] = []
    if visual_hook:
        parts.append(f"Visual hook: {visual_hook.strip()}")
    if concept_arc:
        parts.append(f"Concept arc: {concept_arc.strip()}")
    if character_profile:
        parts.append(f"Character: {character_profile.strip()[:DIRECT_SCENES_CONTEXT_FIELD_CAP]}")
    if brand_design:
        parts.append(f"Brand design: {brand_design.strip()[:DIRECT_SCENES_CONTEXT_FIELD_CAP]}")
    parts.append("")
    parts.append("Slides:")
    parts.append(slides_block)
    parts.append("")
    parts.append(
        "Return ONLY a JSON array; one entry per slide above; "
        "each entry has slide_idx, visual (25-45 words), rationale."
    )

    msg = "\n".join(parts)
    if len(msg) > DIRECT_SCENES_PROMPT_CAP:
        keep = []
        if visual_hook:
            keep.append(f"Visual hook: {visual_hook.strip()}")
        if concept_arc:
            keep.append(f"Concept arc: {concept_arc.strip()}")
        keep.append("")
        keep.append("Slides:")
        keep.append(slides_block)
        keep.append("")
        keep.append(
            "Return ONLY a JSON array; one entry per slide; "
            "each entry has slide_idx, visual (25-45 words), rationale."
        )
        msg = "\n".join(keep)
        if len(msg) > DIRECT_SCENES_PROMPT_CAP:
            head = "\n".join(keep[:-2])
            tail = "\n".join(keep[-2:])
            available = DIRECT_SCENES_PROMPT_CAP - len(head) - len(tail) - 4
            if available > 0:
                msg = head + "\n" + slides_block[:available] + "\n" + tail
            else:
                msg = msg[:DIRECT_SCENES_PROMPT_CAP]
    return msg


def direct_scenes(
    parsed_slides,
    *,
    visual_hook: Optional[str] = None,
    concept_arc: Optional[str] = None,
    brand_design: str,
    character_profile: Optional[str] = None,
    api_key: str = "",
    model: str = "gpt-4o-mini",
) -> SceneDirection:
    """Generate per-slide scene briefs for a parsed script.

    Eager call (Stage 3): visual_hook + concept_arc populated; scene briefs
    use those as the visual through-line. source = "stage_3".
    Lazy call (renderer fallback): visual_hook + concept_arc both None;
    scene briefs inferred from script alone. source = "renderer_fallback".
    """
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")
    if not brand_design:
        raise ValueError("direct_scenes: brand_design is required")

    source = "stage_3" if (visual_hook or concept_arc) else "renderer_fallback"

    user_msg = _build_direct_scenes_user_message(
        parsed_slides=parsed_slides,
        visual_hook=visual_hook,
        concept_arc=concept_arc,
        brand_design=brand_design,
        character_profile=character_profile,
    )

    content = _call_openai(DIRECT_SCENES_SYSTEM_PROMPT, user_msg, api_key, model)
    try:
        slide_visuals = _parse_response_content(content, parsed_slides)
    except ValueError:
        stricter = (
            DIRECT_SCENES_SYSTEM_PROMPT
            + "\n\nIMPORTANT: respond with ONLY valid JSON. No markdown, no code fences."
        )
        content = _call_openai(stricter, user_msg, api_key, model)
        slide_visuals = _parse_response_content(content, parsed_slides)

    briefs = [
        SceneBrief(
            role=sv["slot_role"],
            scene_brief=sv["visual"],
            tone=sv["tone"],
        )
        for sv in slide_visuals
    ]
    return SceneDirection(slides=briefs, source=source)
