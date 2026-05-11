"""Stage 3 script-meta builder for the concept-generator skill.

Reads concept-pick.md + concept-context.json from a run directory; in dry-run
mode writes a format-aware placeholder script.md, a placeholder scene-direction.md,
and the v2 concept-meta.json artifact. In non-dry-run mode, expects script.md to
already exist (host agent writes it) and runs the lint chain (voice_lint +
format_lint + save_filter) before writing concept-meta.json.

Public surface:
    extract_concept_fields(pick_text: str) -> ConceptFields
    build_meta(fields: ConceptFields, brand: str, flags: Flags) -> dict
    write_dry_run_artifacts(run_dir: str, fields: ConceptFields, brand: str, flags: Flags) -> None
    main(argv: list[str] | None = None) -> int  # CLI entry point

CLI usage (invoked from draft_script.sh):
    python3 -m lib.draft_script_meta --run-dir <path> [--mode <interactive|autopilot>]
        [--no-lint] [--no-format-check] [--no-save-filter] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from lib.concept_meta import write_meta


@dataclass(frozen=True)
class ConceptFields:
    fmt: str
    close_action: str
    concept_n: str
    concept_score: float
    claims_personal_fact: bool
    hook_pattern: str
    hook_score: int
    visual_hook: str
    concept_arc: str = ""


@dataclass(frozen=True)
class Flags:
    mode: str = "interactive"
    no_lint: bool = False
    no_format_check: bool = False
    no_save_filter: bool = False
    dry_run: bool = False


# Regex helpers (match the existing draft_script.sh patterns).

_RE_FORMAT = re.compile(r"\*\*Format:\*\*\s*(\S+)", re.IGNORECASE)
_RE_CLOSE_ACTION = re.compile(r"\*\*Close action:\*\*\s*(\S+)", re.IGNORECASE)
_RE_CONCEPT_N = re.compile(r"## Concept (\d+)", re.IGNORECASE)
_RE_CONCEPT_SCORE = re.compile(r"concept_score:\s*([\d.]+)", re.IGNORECASE)
_RE_CLAIMS_PERSONAL = re.compile(r"claims_personal_fact:\s*(true|false)", re.IGNORECASE)
_RE_HOOK = re.compile(
    r"###\s+Hook variants\s*\n\s*1\.\s+\((\w+),\s*shock\s+(\d+)\)",
    re.IGNORECASE,
)
_RE_VISUAL_HOOK = re.compile(r"\*\*Visual hook:\*\*\s*(.+)", re.IGNORECASE)
_RE_ARC = re.compile(r"\*\*Arc:\*\*\s*(.+)", re.IGNORECASE)


def extract_concept_fields(pick_text: str) -> ConceptFields:
    """Parse concept-pick.md content into a ConceptFields struct."""
    def m(pat: re.Pattern, default: str = "") -> str:
        match = pat.search(pick_text)
        return match.group(1).strip() if match else default

    fmt = m(_RE_FORMAT, "narrative")
    close_action = m(_RE_CLOSE_ACTION, "save")
    concept_n = m(_RE_CONCEPT_N, "1")
    concept_score_s = m(_RE_CONCEPT_SCORE, "0")
    claims_personal_s = m(_RE_CLAIMS_PERSONAL, "false")
    visual_hook = m(_RE_VISUAL_HOOK, "")
    concept_arc = m(_RE_ARC, "")

    hook_match = _RE_HOOK.search(pick_text)
    hook_pattern = hook_match.group(1) if hook_match else "single_claim"
    hook_score = int(hook_match.group(2)) if hook_match else 0

    return ConceptFields(
        fmt=fmt,
        close_action=close_action,
        concept_n=concept_n,
        concept_score=float(concept_score_s),
        claims_personal_fact=claims_personal_s.lower() == "true",
        hook_pattern=hook_pattern,
        hook_score=hook_score,
        visual_hook=visual_hook,
        concept_arc=concept_arc,
    )


def _read_concept_context(run_dir: str) -> dict[str, Any]:
    context_path = os.path.join(run_dir, "concept-context.json")
    if not os.path.isfile(context_path):
        return {}
    with open(context_path, encoding="utf-8") as f:
        return json.load(f)


def _read_brand(run_dir: str) -> str:
    return _read_concept_context(run_dir).get("brand", "unknown")


def _read_brand_design(run_dir: str, brand: str) -> str:
    context = _read_concept_context(run_dir)
    for key in ("brand_design", "visual_system", "visual_system_md"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for key in ("brand_design_path", "visual_system_path"):
        value = context.get(key)
        if isinstance(value, str) and value.strip() and os.path.isfile(value):
            with open(value, encoding="utf-8") as f:
                return f.read()

    roots = [
        os.environ.get("SLIDESHOW_BRANDS_ROOT", ""),
        os.environ.get("BRANDS_ROOT", ""),
        os.path.join(os.path.expanduser("~"), ".clawd", "brands"),
        os.path.join(os.path.expanduser("~"), "Documents", "GitHub", "slideshow-brands"),
    ]
    for root in roots:
        if not root:
            continue
        path = os.path.join(root, brand, "visual-system.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return f.read()

    return f"brand: {brand}\nvisual system unavailable"


def build_meta(fields: ConceptFields, brand: str, flags: Flags) -> dict[str, Any]:
    """Build the concept-meta dict for write_meta."""
    return {
        "format": fields.fmt,
        "close_action": fields.close_action,
        "hook_pattern": fields.hook_pattern,
        "hook_score": fields.hook_score,
        "concept_score": fields.concept_score,
        "claims_personal_fact": fields.claims_personal_fact,
        "concept_id": f"concept_{fields.concept_n}",
        "brand": brand,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "save_filter_skipped": flags.no_save_filter,
        "lint_skipped": flags.no_lint,
        "format_check_skipped": flags.no_format_check,
        "visual_hook": fields.visual_hook,
        "concept_arc": fields.concept_arc,
        "scene_direction_source": "stage_3",
    }


def _format_aware_placeholder(fields: ConceptFields) -> str:
    """Return a minimal format-compatible script.md body."""
    if fields.fmt == "numbered_diagnostic":
        sections = [
            "# HOOK\nthe four tells of every AI carousel. once you see them you cant unsee.\n",
            "# TELL #1\ntell #1: 6 slides. always 6. real carousels are sized to the story.\n",
            "# TELL #2\ntell #2: stock backgrounds. nobody's brand actually looks like that.\n",
            "# TELL #3\ntell #3: slide 4 always says nothing. the model could not think of a real beat.\n",
            "# TELL #4\ntell #4: it ends on a steve jobs quote. the model could not write a real ending.\n",
            "# FIX\nthe fix is structural. 3 questions before you ship: does slide 1 open a loop? does slide 4 do real work? does slide 7 close it?\n",
            "# CTA\nsave this. run the 3-question audit on your next 3 carousels before you post.\n",
        ]
    else:
        sections = [
            "# HOOK\nthe four tells of every AI carousel. once you see them you cant unsee.\n",
            "# BODY\nfor every carousel this week the same four patterns showed up. dated tuesday afternoon. counted twelve in ten minutes. the operator pattern is real.\n",
            "# CTA\nsave this. audit your last three carousels before you post the next one.\n",
        ]
    return (
        "---\n"
        f"format: {fields.fmt}\n"
        f"close_action: {fields.close_action}\n"
        "---\n\n"
        + "\n".join(sections)
    )


def write_dry_run_artifacts(
    run_dir: str,
    fields: ConceptFields,
    brand: str,
    flags: Flags,
) -> None:
    """Write script.md placeholder + scene-direction.md + concept-meta.json."""
    script_md = os.path.join(run_dir, "script.md")
    scene_md = os.path.join(run_dir, "scene-direction.md")

    with open(script_md, "w", encoding="utf-8") as f:
        f.write(_format_aware_placeholder(fields))

    placeholder_scene = (
        "# Scene direction (source: stage_3)\n\n"
        "## Slide 1 (HOOK)\n"
        "**Tone:** observational\n"
        f"**Scene:** {fields.visual_hook or 'placeholder for dry-run'}\n\n"
        "## Slide 2 (CTA)\n"
        "**Tone:** punchy\n"
        "**Scene:** closeup of laptop screen, bookmark icon highlighted.\n"
    )
    with open(scene_md, "w", encoding="utf-8") as f:
        f.write(placeholder_scene)

    meta = build_meta(fields, brand, flags)
    write_meta(run_dir, meta)


def _split_script_into_slides(script_text: str) -> list[tuple[str, str]]:
    """Walk script.md line-by-line, return list of (role, body) tuples.

    Headings are lines starting with `# `. Role is extracted via the same
    rule format-lint uses: alphabetic prefix, uppercased, digits/underscores
    stripped (e.g., `# TELL #1` -> "TELL").
    """
    from lib.format_lint import _heading_role_token

    sections: list[tuple[str, str]] = []
    current_role: str | None = None
    current_body: list[str] = []

    for line in script_text.splitlines():
        if line.startswith("# "):
            if current_role is not None:
                sections.append((current_role, "\n".join(current_body).strip()))
            token = _heading_role_token(line)
            current_role = token or ""
            current_body = []
        elif current_role is not None:
            current_body.append(line)

    if current_role is not None:
        sections.append((current_role, "\n".join(current_body).strip()))

    return sections


def _resolve_effective_word_cap(fmt: str, role: str, run_dir: str, flags: Flags) -> int:
    """Resolve the effective word_count_max for a (format, role) pair.

    Layers (last wins):
      1. format YAML's slot.word_count_max (default), looked up via slot.aliases
         so heading tokens like 'TELL' resolve to canonical slot 'ITEM'.
      2. brands/<slug>/styles/<style>/style.yaml word_count_override (if
         BRAND_STYLE_DIR is set).

    Falls back to 50 when format/role lookup fails.
    """
    try:
        from lib.format_registry import get_format
        fmt_def = get_format(fmt)
    except Exception:
        return 50

    # Match the heading-token role against each slot's aliases; canonical
    # role names are also present in their own aliases list.
    slot = next((s for s in fmt_def.slots if role in s.aliases), None)
    if slot is None:
        return 50

    base_max = slot.word_count_max
    base_min = slot.word_count_min

    style_dir = os.environ.get("BRAND_STYLE_DIR")
    if style_dir:
        try:
            from lib.style_overrides import (
                load_style_overrides,
                merge_word_count_override,
            )
            overrides = load_style_overrides(style_dir)
            # style.yaml may key overrides by canonical role or alias; try both.
            override = overrides.get(slot.role) or overrides.get(role)
            merged = merge_word_count_override((base_min, base_max), override)
            return merged[1]
        except Exception:
            pass

    return base_max


def _run_lint_chain(run_dir: str, fields: ConceptFields, flags: Flags) -> int:
    """Run voice_lint + format_lint + save_filter on script.md.

    Slide bodies are split by heading tokens using the same
    format_lint._heading_role_token contract as the structure checker.
    save_filter resolves each slot cap through _resolve_effective_word_cap,
    including BRAND_STYLE_DIR style.yaml overrides when that env var is set.
    Any voice, format, or save-filter violation aborts with return code 1.

    Returns 0 on clean lint, 1 on any violations.
    """
    script_md = os.path.join(run_dir, "script.md")
    if not os.path.isfile(script_md):
        print(f"[ERR] script.md not found in {run_dir}", file=sys.stderr)
        return 1
    with open(script_md, encoding="utf-8") as f:
        script_text = f.read()

    all_violations = []

    # voice_lint
    if not flags.no_lint:
        from lib.voice_lint import lint_text
        all_violations.extend(lint_text(script_text))

    # format_lint
    if not flags.no_format_check:
        from lib.format_lint import lint_script_structure
        # Stage 3 caller may set BRAND_STYLE_DIR env var; respect it if present.
        style_dir = os.environ.get("BRAND_STYLE_DIR")
        all_violations.extend(
            lint_script_structure(
                script_text,
                fields.fmt,
                fields.close_action,
                style_dir=style_dir,
            )
        )

    # save_filter (NEW in v0.8.1)
    if not flags.no_save_filter:
        from lib.save_filter import check_save_worthiness
        for role, body in _split_script_into_slides(script_text):
            if not body:
                continue
            slot_cap = _resolve_effective_word_cap(fields.fmt, role, run_dir, flags)
            all_violations.extend(
                check_save_worthiness(
                    slide_role=role,
                    slide_body=body,
                    effective_word_cap_max=slot_cap,
                )
            )

    if all_violations:
        for v in all_violations:
            print(f"[lint] {v.rule_id}: {v.message}", file=sys.stderr)
        return 1
    return 0


def _write_scene_direction_artifact(
    run_dir: str,
    fields: ConceptFields,
    brand_design: str,
) -> None:
    from lib.visual_director import (
        SceneBrief,
        SceneDirection,
        direct_scenes,
        scene_direction_to_markdown,
    )

    script_md = os.path.join(run_dir, "script.md")
    with open(script_md, encoding="utf-8") as f:
        script_text = f.read()
    parsed_slides = _split_script_into_slides(script_text)

    try:
        scene_direction = direct_scenes(
            parsed_slides=parsed_slides,
            visual_hook=fields.visual_hook,
            concept_arc=fields.concept_arc,
            brand_design=brand_design,
        )
    except Exception as e:
        print(
            f"[WARN] direct_scenes failed during stage_3 ({type(e).__name__}: {e}); "
            "writing deterministic scene-direction.md fallback.",
            file=sys.stderr,
        )
        fallback_base = fields.visual_hook or fields.concept_arc or "script beat"
        scene_direction = SceneDirection(
            slides=[
                SceneBrief(
                    role=role,
                    scene_brief=(
                        f"{fallback_base}. Frame this {role.lower()} slide around "
                        "the exact copy, with one clear focal point and no extra CTA cues."
                    ),
                    tone="neutral",
                )
                for role, _body in parsed_slides
            ],
            source="stage_3",
        )
    scene_md = os.path.join(run_dir, "scene-direction.md")
    with open(scene_md, "w", encoding="utf-8") as f:
        f.write(scene_direction_to_markdown(scene_direction))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage 3 script-meta builder")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--mode", default="interactive")
    p.add_argument("--no-lint", action="store_true")
    p.add_argument("--no-format-check", action="store_true")
    p.add_argument("--no-save-filter", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run_dir = args.run_dir
    if not os.path.isdir(run_dir):
        print(f"[ERR] run-dir not found: {run_dir}", file=sys.stderr)
        return 1
    pick_md = os.path.join(run_dir, "concept-pick.md")
    if not os.path.isfile(pick_md):
        print(f"[ERR] concept-pick.md not found in {run_dir}", file=sys.stderr)
        return 1

    with open(pick_md, encoding="utf-8") as f:
        pick_text = f.read()
    fields = extract_concept_fields(pick_text)
    brand = _read_brand(run_dir)
    flags = Flags(
        mode=args.mode,
        no_lint=args.no_lint,
        no_format_check=args.no_format_check,
        no_save_filter=args.no_save_filter,
        dry_run=args.dry_run,
    )

    if flags.dry_run:
        write_dry_run_artifacts(run_dir, fields, brand, flags)
        print(f"[OK] dry-run script.md + scene-direction.md + concept-meta.json -> {run_dir}")
        return 0

    # Non-dry-run: run the lint chain on the script.md the host agent wrote.
    lint_status = _run_lint_chain(run_dir, fields, flags)
    if lint_status != 0:
        return lint_status
    _write_scene_direction_artifact(run_dir, fields, _read_brand_design(run_dir, brand))
    # Lint passed, scene-direction.md written, now write concept-meta.json.
    meta = build_meta(fields, brand, flags)
    write_meta(run_dir, meta)
    print(f"[OK] script.md validated; scene-direction.md + concept-meta.json -> {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
