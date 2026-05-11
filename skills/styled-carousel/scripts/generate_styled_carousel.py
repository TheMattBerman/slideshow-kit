#!/usr/bin/env python3
"""Generate a styled carousel: resolve style, compose prompts, call gpt-image-2.

Inputs come from CLI flags (see argparse). Output is PNGs + prompts.json +
output-log.json in the output dir.
"""

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from typing import Optional

# Make the repo root importable so we can use lib/.
KIT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, KIT_DIR)

# gpt_image_2 lives alongside this script (skills/styled-carousel/scripts/).
HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)

from lib.design_md_parser import parse
from lib.style_resolver import resolve_with_artifact
from lib.voice_lint import lint_text
from lib.format_lint import lint_script_structure
from lib.visual_director import (
    CHARACTER_DRIVEN_TREATMENTS,
    SceneDirection,
    direct_scenes,
    scene_direction_from_markdown,
    scene_direction_to_markdown,
)
import gpt_image_2  # type: ignore[reportMissingImports]
import script_parser  # type: ignore[reportMissingImports]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--brand", required=True)
    p.add_argument("--style", default=None,
                   help="Style name. Falls back to brand default_style, then 'social_native'.")
    p.add_argument("--script", required=True, help="Path to script markdown")
    p.add_argument("--output", default=None, help="Output directory")
    p.add_argument("--sizes", default=None,
                   help="Comma-separated sizes")
    p.add_argument("--provider", default="auto",
                   choices=["auto", "api", "codex-native"],
                   help="Image provider. auto uses codex-native inside Codex Desktop, api elsewhere.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--brands-root", default=None,
                   help="Override brands_root (default: $SLIDESHOW_BRANDS_ROOT or ./brands)")
    p.add_argument("--no-lint", action="store_true",
                   help="Skip the pre-render voice lint (logged as lint_skipped in output-log.json).")
    p.add_argument("--no-format-check", action="store_true",
                   help="Skip the format-aware structure lint.")
    p.add_argument("--no-visual-director", action="store_true",
                   help="Skip the visual-director LLM call; use generic per-slide framing.")
    return p.parse_args()


def resolve_brands_root(override: Optional[str] = None) -> str:
    if override:
        return override
    return os.environ.get("SLIDESHOW_BRANDS_ROOT", "./brands")


def resolve_active_style(brand_dir: str, style_arg: Optional[str] = None) -> str:
    """Resolve the active style name. Order: --style flag, config default, social_native."""
    if style_arg:
        return style_arg
    config_path = os.path.join(brand_dir, "config.json")
    if os.path.isfile(config_path):
        with open(config_path) as f:
            cfg = json.load(f)
        if cfg.get("default_style"):
            return cfg["default_style"]
    return "social_native"


ASPECT_RATIO_SIZES = {
    "9:16": "768x1344",
    "1:1": "1024x1024",
    "4:5": "1024x1280",
    "16:9": "1536x864",
}
FALLBACK_SIZE = "1024x1536"
NATIVE_REQUESTS_FILE = "native-generation-requests.json"


def resolve_sizes(sizes_arg: Optional[str], tokens: dict) -> list[str]:
    """Resolve renderer sizes from CLI or style tokens."""
    if sizes_arg:
        return [s.strip() for s in sizes_arg.split(",") if s.strip()]

    output_size = tokens.get("output_size")
    if isinstance(output_size, str) and output_size.strip():
        return [output_size.strip()]

    aspect_ratio = tokens.get("aspect_ratio")
    if isinstance(aspect_ratio, str):
        mapped = ASPECT_RATIO_SIZES.get(aspect_ratio.strip())
        if mapped:
            return [mapped]

    return [FALLBACK_SIZE]


def is_codex_desktop_env(env: Optional[dict] = None) -> bool:
    """Return True when running inside the Codex desktop app shell."""
    values = env if env is not None else os.environ
    originator = values.get("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "")
    return (
        originator == "Codex Desktop"
        and bool(values.get("CODEX_THREAD_ID"))
        and values.get("CODEX_SHELL") == "1"
    )


def resolve_generation_provider(provider_arg: str, dry_run: bool) -> str:
    """Resolve image provider for this run."""
    if dry_run:
        return "dry-run"
    if provider_arg != "auto":
        return provider_arg
    if is_codex_desktop_env():
        return "codex-native"
    return "api"


def style_dir_for(brand_dir: str, style_name: str, kit_dir: str) -> str:
    """Return the style directory path. Brand-local first, then kit reference."""
    brand_local = os.path.join(brand_dir, "styles", style_name)
    if os.path.isdir(brand_local):
        return brand_local
    kit_ref = os.path.join(kit_dir, "references", "styles", style_name)
    if os.path.isdir(kit_ref):
        return kit_ref
    raise FileNotFoundError(
        f"style '{style_name}' not found in {brand_local} or {kit_ref}")


def load_refs(style_dir: str, cap: int = 5) -> list:
    """Return up to `cap` ref image paths, sorted alphabetically."""
    refs_dir = os.path.join(style_dir, "refs")
    if not os.path.isdir(refs_dir):
        print(f"[WARN] {refs_dir} missing; generating without visual refs", file=sys.stderr)
        return []
    paths = sorted(glob.glob(os.path.join(refs_dir, "*.png"))
                   + glob.glob(os.path.join(refs_dir, "*.jpg"))
                   + glob.glob(os.path.join(refs_dir, "*.jpeg")))
    if len(paths) > cap:
        print(f"[INFO] {len(paths)} refs found; truncating to first {cap}", file=sys.stderr)
        paths = paths[:cap]
    return paths


_META_HEADINGS = [
    "When to swap to a different style",
    "When to swap",
    "Style swap guidance",
]


def strip_meta_sections(style_body: str) -> str:
    """Remove meta-guidance sections (e.g. '## When to swap') from a style body.

    A section starts at a heading whose title (case-insensitive) matches one
    of _META_HEADINGS, and ends at the next '## ' heading or end of file.
    """
    lines = style_body.splitlines(keepends=True)
    out: list = []
    i = 0
    while i < len(lines):
        line = lines[i]
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match and match.group(1).lower() in {h.lower() for h in _META_HEADINGS}:
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            continue
        out.append(line)
        i += 1
    return "".join(out)


def serialize_tokens(tokens: dict) -> str:
    """Render the token dict as a constraint list for the prompt."""
    lines = []

    def walk(prefix: str, node) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(f"{prefix}.{k}" if prefix else k, v)
        else:
            lines.append(f"{prefix}: {node}")

    walk("", tokens)
    return "\n".join(lines)


# Framing templates keyed on the style's image_treatment token.
# When a style's image_treatment matches a key here, that framing replaces the
# default. Unknown/missing image_treatment falls back to DEFAULT_FRAMING_KEY.
FRAMING_TEMPLATES = {
    "screenshot_native": (
        "This slide is a typography-driven social carousel slide. Render the slide "
        "text below verbatim as the foreground typography of the composition. Do NOT "
        "illustrate or visualize the words: do NOT add icons, charts, grids, mockups, "
        "or imagery referenced in the text. The text IS the design."
    ),
    "iphone_candid": (
        "Candid iPhone-style photograph of the man shown in the reference images. "
        "Same beard, same hair, same wardrobe across the entire carousel.\n\n"
        "Scene: {visual}\n\n"
        "Render this exact text as clean typography integrated into the photograph. "
        "Place it where the negative space allows (top, bottom, or beside the "
        "figure). White or near-white sans-serif (system-ui, Inter, SF Pro). "
        "Do not paraphrase, abbreviate, or summarize the text. Render every word.\n\n"
        "Text:\n"
        "\"{caption_text}\"\n\n"
        "Vertical 9:16 aspect ratio."
    ),
}

DEFAULT_FRAMING_KEY = "screenshot_native"


def _resolve_framing(tokens: dict, caption_text: str,
                     visual: Optional[str] = None) -> str:
    """Return the framing paragraph for this style's image_treatment.

    Templates may contain `{caption_text}` and/or `{visual}` slots. We
    substitute them via plain string .replace() (not .format()) because the
    template may contain stray `{` or `}` from prompt punctuation.

    Falls back to the default (screenshot_native / type-forward) framing when
    the style's image_treatment is missing or not recognized. When `visual`
    is None, the iphone_candid template substitutes a generic
    character-anchored fallback string.
    """
    treatment = tokens.get("image_treatment")
    template = (
        FRAMING_TEMPLATES.get(treatment) if isinstance(treatment, str) else None
    )
    if template is None:
        template = FRAMING_TEMPLATES[DEFAULT_FRAMING_KEY]
    if "{caption_text}" in template:
        template = template.replace("{caption_text}", caption_text)
    if "{visual}" in template:
        substitution = visual or (
            "a candid moment that fits the slide's beat. Pose, expression, "
            "scene, and crop should vary from other slides in the carousel"
        )
        template = template.replace("{visual}", substitution)
    return template


def compose_prompt(tokens: dict, style_body: str, role: str, body: str,
                   slide_idx: int, total_slides: int,
                   visual: Optional[str] = None) -> str:
    treatment = tokens.get("image_treatment", "")
    if not isinstance(treatment, str):
        treatment = ""

    framing = _resolve_framing(tokens, body, visual)

    if treatment == "iphone_candid":
        # v0.7.5: slim prompt for character-driven slides. The framing template
        # already contains the visual + the exact caption + the no-paraphrase
        # directive. Drop the YAML token dump and the DESIGN.md verbatim body:
        # both are noise for the image model on photo-driven slides and were
        # competing with the load-bearing rendering instructions.
        out = ["# Slide intent", framing]
        return "\n".join(out)

    diet_body = strip_meta_sections(style_body)
    out = [
        "# Slide intent",
        f"slide {slide_idx + 1} of {total_slides}, role: {role}",
        "",
        framing,
        "",
        "slide text:",
        f'"{body}"',
        "",
        "# Tokens",
        serialize_tokens(tokens),
        "",
        "# Style intent",
        diet_body,
    ]
    return "\n".join(out)


def call_gpt_image_2(prompt: str, ref_paths: list, size: str, output_path: str,
                     dry_run: bool) -> dict:
    """Generate one image via gpt-image-2.

    Lifted from the pre-rename generate_branded_carousel.py: the original call was
    gpt_image_2.generate(prompt, size, output_path, api_key, dry_run=dry_run).
    reference_images=ref_paths is the only addition.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    return gpt_image_2.generate(
        prompt=prompt,
        size=size,
        output_path=output_path,
        api_key=api_key,
        dry_run=dry_run,
        reference_images=ref_paths,
    )


def write_native_generation_requests(output_dir: str, requests: list[dict]) -> None:
    """Write Codex-native image generation handoff manifest."""
    path = os.path.join(output_dir, NATIVE_REQUESTS_FILE)
    manifest = {
        "_schema_version": 1,
        "provider": "codex-native",
        "status": "pending",
        "instructions": (
            "Codex Desktop should generate each request with native image generation "
            "and save the PNG exactly at output_path."
        ),
        "requests": requests,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def main() -> int:
    args = parse_args()
    brands_root = resolve_brands_root(args.brands_root)
    brand_dir = os.path.join(brands_root, args.brand)
    if not os.path.isdir(brand_dir):
        print(f"[FAIL] brand workspace not found: {brand_dir}", file=sys.stderr)
        return 1

    style_name = resolve_active_style(brand_dir, args.style)
    try:
        style_dir = style_dir_for(brand_dir, style_name, KIT_DIR)
    except FileNotFoundError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 1
    style_design = os.path.join(style_dir, "DESIGN.md")
    brand_design = os.path.join(brand_dir, "visual-system.md")

    if not os.path.isfile(style_design):
        print(f"[FAIL] style DESIGN.md missing: {style_design}", file=sys.stderr)
        return 1
    if not os.path.isfile(brand_design):
        print(f"[FAIL] brand visual-system.md missing: {brand_design}", file=sys.stderr)
        return 1

    style_body = parse(style_design).body

    # v0.6.1: pre-render voice lint runs first (before parse + format lint).
    lint_skipped = False
    if args.no_lint:
        lint_skipped = True
    else:
        brand_voice_path = os.path.join(brand_dir, "brand-voice.md")
        brand_voice_arg = brand_voice_path if os.path.exists(brand_voice_path) else None
        with open(args.script) as f:
            script_text = f.read()
        violations = lint_text(script_text, brand_voice_path=brand_voice_arg)
        if violations:
            for v in violations:
                print(f"{args.script}:{v.line}:{v.column} [{v.rule_id}] {v.message}",
                      file=sys.stderr)
            return 1

    # v0.7.0: format-aware parse + structure lint.
    format_check_skipped = False
    try:
        parsed = script_parser.parse_script(args.script)
    except ValueError as e:
        if args.no_format_check:
            print(f"{args.script}: parse error: {e}", file=sys.stderr)
            return 1
        print(f"{args.script}: parse error: {e}", file=sys.stderr)
        return 1

    if args.no_format_check:
        format_check_skipped = True
    else:
        with open(args.script) as f:
            full_script_text = f.read()
        # Strip frontmatter for lint (same body the walker sees).
        body_for_lint = full_script_text
        if body_for_lint.startswith("---"):
            parts = body_for_lint.split("---", 2)
            if len(parts) >= 3:
                body_for_lint = parts[2]
        brand_voice_path = os.path.join(brand_dir, "brand-voice.md")
        bv_arg = brand_voice_path if os.path.exists(brand_voice_path) else None
        style_dir_for_lint = (
            os.path.join(brand_dir, "styles", style_name)
            if os.path.isdir(os.path.join(brand_dir, "styles", style_name))
            else None
        )
        format_violations = lint_script_structure(
            body_for_lint,
            parsed.format_name,
            parsed.close_action,
            brand_voice_path=bv_arg,
            style_dir=style_dir_for_lint,
        )
        if format_violations:
            for v in format_violations:
                print(f"{args.script}:{v.line}:{v.column} [{v.rule_id}] {v.message}",
                      file=sys.stderr)
            return 1

    sections = [(slide.slot_role, slide.body) for slide in parsed.slides]
    if not sections:
        print(f"[FAIL] no slide sections found in {args.script}", file=sys.stderr)
        return 1

    output_dir = args.output or os.path.join(
        brand_dir, "runs", dt.date.today().isoformat())
    os.makedirs(output_dir, exist_ok=True)

    tokens = resolve_with_artifact(brand_design, style_design, output_dir)
    sizes = resolve_sizes(args.sizes, tokens)
    generation_provider = resolve_generation_provider(args.provider, args.dry_run)
    refs = load_refs(style_dir)

    # v0.8.0: scene-direction.md cache + lazy direct_scenes fallback.
    image_treatment = tokens.get("image_treatment", "")
    scene_direction: Optional[SceneDirection] = None
    scene_direction_source = ""
    scene_md_path = os.path.join(output_dir, "scene-direction.md")

    # Path 1: pre-existing scene-direction.md wins (typically from Stage 3).
    if os.path.isfile(scene_md_path):
        try:
            with open(scene_md_path, encoding="utf-8") as f:
                scene_direction = scene_direction_from_markdown(f.read())
            scene_direction_source = scene_direction.source
            print(
                f"[INFO] using pre-existing scene-direction.md (source: {scene_direction_source})",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"[WARN] failed to parse scene-direction.md: {e}; will regenerate",
                file=sys.stderr,
            )
            scene_direction = None

    # Path 2: lazy fallback. Character-driven, --no-visual-director not set,
    # and NOT in dry-run (would make an API call otherwise).
    is_character_driven = (
        isinstance(image_treatment, str)
        and image_treatment in CHARACTER_DRIVEN_TREATMENTS
    )
    if (
        scene_direction is None
        and is_character_driven
        and not args.no_visual_director
        and not args.dry_run
    ):
        character_path = os.path.join(brand_dir, "characters", "character-default.md")
        if os.path.isfile(character_path):
            with open(character_path, encoding="utf-8") as f:
                character_profile: Optional[str] = f.read()
        else:
            character_profile = None
        design_path = os.path.join(brand_dir, "DESIGN.md")
        if os.path.isfile(design_path):
            with open(design_path, encoding="utf-8") as f:
                brand_design_text = f.read()
        else:
            brand_design_text = ""
        try:
            scene_direction = direct_scenes(
                parsed_slides=[
                    (s.slot_role, s.body, s.heading) for s in parsed.slides
                ],
                brand_design=brand_design_text,
                character_profile=character_profile,
                api_key=os.environ.get("OPENAI_API_KEY", ""),
            )
            with open(scene_md_path, "w", encoding="utf-8") as f:
                f.write(scene_direction_to_markdown(scene_direction))
            scene_direction_source = scene_direction.source
            print(
                f"[INFO] generated scene-direction.md via lazy fallback "
                f"({len(scene_direction.slides)} slides)",
                file=sys.stderr,
            )
        except Exception as e:
            print(
                f"[WARN] direct_scenes failed ({e}); falling back to generic framing",
                file=sys.stderr,
            )

    # Path 3: build visuals_by_idx from scene_direction (compat with v0.7.4 path).
    visuals_by_idx: dict[int, str] = {}
    visual_director_used = False
    if scene_direction is not None:
        visuals_by_idx = {
            i: brief.scene_brief
            for i, brief in enumerate(scene_direction.slides)
        }
        visual_director_used = bool(visuals_by_idx)

    prompts_log: dict = {}
    slide_results: list = []
    native_requests: list[dict] = []
    completed = 0
    failed = 0

    try:
        for idx, (role, body) in enumerate(sections):
            visual = visuals_by_idx.get(idx)
            prompt = compose_prompt(
                tokens, style_body, role, body, idx, len(sections), visual=visual,
            )
            prompts_log[f"slide-{idx + 1:02d}"] = {
                "role": role,
                "prompt": prompt,
                "refs": [os.path.basename(p) for p in refs],
            }
            for size in sizes:
                output_path = os.path.join(
                    output_dir, f"{style_name}-slide-{idx + 1:02d}-{size}.png")
                entry = {
                    "slide_idx": idx,
                    "slide_number": idx + 1,
                    "role": role,
                    "size": size,
                    "output_path": output_path,
                    "status": "pending",
                    "error": None,
                }
                if generation_provider == "codex-native":
                    entry["status"] = "pending_codex_native"
                    native_requests.append({
                        "slide_idx": idx,
                        "slide_number": idx + 1,
                        "role": role,
                        "size": size,
                        "output_path": output_path,
                        "prompt": prompt,
                        "reference_images": refs,
                    })
                else:
                    try:
                        call_gpt_image_2(prompt, refs, size, output_path, args.dry_run)
                        entry["status"] = "ok"
                    except SystemExit as e:
                        # gpt_image_2.generate() calls sys.exit(1) on unrecoverable
                        # failure. Capture and continue to the next slide; surface
                        # in output-log.
                        code = e.code if hasattr(e, "code") else 1
                        entry["status"] = "failed"
                        entry["error"] = f"gpt-image-2 call failed (sys.exit {code})"
                        print(
                            f"[WARN] slide {idx + 1} ({role}) failed; continuing with remaining slides",
                            file=sys.stderr,
                        )
                    except Exception as e:
                        entry["status"] = "failed"
                        entry["error"] = f"{type(e).__name__}: {e}"
                        print(
                            f"[WARN] slide {idx + 1} ({role}) raised {type(e).__name__}: {e}; continuing",
                            file=sys.stderr,
                        )
                slide_results.append(entry)
    finally:
        completed = sum(1 for r in slide_results if r["status"] == "ok")
        failed = sum(1 for r in slide_results if r["status"] == "failed")
        requested = sum(
            1 for r in slide_results if r["status"] == "pending_codex_native"
        )

        if native_requests:
            write_native_generation_requests(output_dir, native_requests)

        with open(os.path.join(output_dir, "prompts.json"), "w") as f:
            json.dump(prompts_log, f, indent=2)

        with open(os.path.join(output_dir, "output-log.json"), "w") as f:
            json.dump({
                "brand": args.brand,
                "style": style_name,
                "slides": len(sections),
                "slide_count": len(sections),
                "slides_completed": completed,
                "slides_failed": failed,
                "slides_requested": requested,
                "sizes": sizes,
                "dry_run": args.dry_run,
                "generation_provider": generation_provider,
                "native_generation_requests": (
                    NATIVE_REQUESTS_FILE if native_requests else None
                ),
                "lint_skipped": lint_skipped,
                "format_name": parsed.format_name,
                "close_action": parsed.close_action,
                "format_check_skipped": format_check_skipped,
                "visual_director_used": visual_director_used,
                "scene_direction_source": scene_direction_source,
                "slide_results": slide_results,
                "ended_at": dt.datetime.now(dt.timezone.utc)
                              .strftime("%Y-%m-%dT%H:%M:%SZ"),
            }, f, indent=2)

    if failed:
        print(
            f"[PARTIAL] {completed} of {len(sections)} slide(s) rendered in {style_name} style; "
            f"{failed} failed (see output-log.json)",
            file=sys.stderr,
        )
        return 1
    if native_requests:
        print(
            f"[HANDOFF] {len(native_requests)} Codex-native image request(s) written to "
            f"{os.path.join(output_dir, NATIVE_REQUESTS_FILE)}"
        )
        return 0
    print(f"[PASS] {completed} slide(s) x {len(sizes)} size(s) in {style_name} style")
    return 0


if __name__ == "__main__":
    sys.exit(main())
