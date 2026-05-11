#!/usr/bin/env python3
"""Three-variant face-continuity diagnostic.

Runs the same script through control / batch / anchor-chain pipelines.
Saves outputs to <output-root>/{control,batch,anchor}/.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "skills", "branded-carousel", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "skills", "social-native-carousel", "scripts"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gpt_image_2  # type: ignore[reportMissingImports]
import snc_script_parser  # type: ignore[reportMissingImports]
import snc_prompt_builder  # type: ignore[reportMissingImports]
import character_io  # type: ignore[reportMissingImports]
import face_crop  # type: ignore[reportMissingImports]
import _brands_root  # type: ignore[reportMissingImports]


SIZE = "1024x1024"


def _load_inputs(brand: str, script_path: str):
    brand_dir = _brands_root.brand_dir(brand)
    char_dir = os.path.join(brand_dir, "characters")
    char_files = sorted(
        f for f in os.listdir(char_dir)
        if f.endswith(".md") and not f.startswith(".")
    )
    if not char_files:
        raise SystemExit(f"no character file in {char_dir}")
    char_path = os.path.join(char_dir, char_files[0])
    character = character_io.load(char_path)
    refs = character_io.resolve_reference_paths(character, char_path)
    if not refs:
        raise SystemExit(f"no usable reference images for character {char_path}")
    parsed = snc_script_parser.parse(script_path)
    return character, refs, parsed


def _slug(role: str) -> str:
    return role.lower().replace("_", "-")


def run_control(out_dir: str, character, refs, parsed, api_key: str):
    os.makedirs(out_dir, exist_ok=True)
    log = []
    roles = list(parsed.keys())
    for idx, role in enumerate(roles, start=1):
        prompt = snc_prompt_builder.build(
            slide_role=role, slide_index=idx, total_slides=len(roles),
            copy_text=parsed[role], character=character, size=SIZE,
        )
        out = os.path.join(out_dir, f"slide-{idx:02d}-{_slug(role)}.png")
        result = gpt_image_2.generate(
            prompt=prompt, size=SIZE, output_path=out,
            api_key=api_key, reference_images=refs, n=1,
        )
        log.append({"slide": idx, "role": role, "result": result})
    return log


def run_batch(out_dir: str, character, refs, parsed, api_key: str):
    os.makedirs(out_dir, exist_ok=True)
    panels = [(role, parsed[role]) for role in parsed.keys()]
    prompt = snc_prompt_builder.build_multi_panel(
        panels=panels, character=character, size=SIZE,
    )
    out = os.path.join(out_dir, "slide.png")
    result = gpt_image_2.generate(
        prompt=prompt, size=SIZE, output_path=out,
        api_key=api_key, reference_images=refs, n=len(panels),
    )
    out_paths = result.get("output_paths") or []
    renamed = []
    for i, p in enumerate(out_paths, start=1):
        role = list(parsed.keys())[i - 1] if i - 1 < len(parsed) else f"panel-{i}"
        new_name = os.path.join(out_dir, f"slide-{i:02d}-{_slug(role)}.png")
        if p != new_name:
            os.rename(p, new_name)
        renamed.append(new_name)
    return [{"batch_result": result, "renamed": renamed}]


def run_anchor_chain(out_dir: str, character, refs, parsed, api_key: str):
    os.makedirs(out_dir, exist_ok=True)
    log = []
    roles = list(parsed.keys())
    prev_face_crop = None
    for idx, role in enumerate(roles, start=1):
        prompt = snc_prompt_builder.build(
            slide_role=role, slide_index=idx, total_slides=len(roles),
            copy_text=parsed[role], character=character, size=SIZE,
        )
        if prev_face_crop is not None:
            prompt += (
                "\n\nADDITIONAL ANCHOR: a second reference image is attached "
                "showing the subject's face crop from the previous slide. "
                "Use BOTH reference images for IDENTITY ONLY. Do not inherit "
                "either image's setting, wardrobe, or framing."
            )
        these_refs = list(refs)
        if prev_face_crop is not None:
            these_refs.append(prev_face_crop)
        out = os.path.join(out_dir, f"slide-{idx:02d}-{_slug(role)}.png")
        result = gpt_image_2.generate(
            prompt=prompt, size=SIZE, output_path=out,
            api_key=api_key, reference_images=these_refs, n=1,
        )
        crop_path = os.path.join(out_dir, f".face-crop-{idx:02d}.png")
        face_crop.crop_face_region(out, crop_path)
        prev_face_crop = crop_path
        log.append({"slide": idx, "role": role, "result": result, "anchor_used": prev_face_crop})
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--variants", default="control,batch,anchor",
                    help="comma-separated subset to run")
    args = ap.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY required")

    character, refs, parsed = _load_inputs(args.brand, args.script)

    runners = {
        "control": run_control,
        "batch": run_batch,
        "anchor": run_anchor_chain,
    }
    selected = [v.strip() for v in args.variants.split(",") if v.strip()]

    if "anchor" in selected:
        try:
            face_crop._imagemagick_cmd()
        except RuntimeError as e:
            print(
                f"[FAIL] anchor variant requires ImageMagick: {e}\n"
                f"Install: brew install imagemagick",
                file=sys.stderr,
            )
            sys.exit(1)

    summary = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "brand": args.brand,
        "script": os.path.abspath(args.script),
        "output_root": os.path.abspath(args.output_root),
        "variants": {},
    }
    os.makedirs(args.output_root, exist_ok=True)

    for v in selected:
        if v not in runners:
            print(f"[SKIP] unknown variant {v}", file=sys.stderr)
            continue
        out_dir = os.path.join(args.output_root, v)
        print(f"[RUN] variant={v} out_dir={out_dir}", file=sys.stderr)
        log = runners[v](out_dir, character, refs, parsed, api_key)
        summary["variants"][v] = log

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    with open(os.path.join(args.output_root, "diagnostic-log.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[PASS] wrote {args.output_root}/diagnostic-log.json")


if __name__ == "__main__":
    main()
