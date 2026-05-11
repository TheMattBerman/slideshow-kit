#!/usr/bin/env python3
"""Validate a brand workspace has all required DNA files and sections."""
import argparse
import os
import re
import sys

VOICE_SECTIONS = [
    "# Voice Principles", "# Structure", "# Signature Patterns",
    "# What NOT to Do", "# Length / Format"
]
PERSPECTIVE_SECTIONS = [
    "# ICP", "# Pillars", "# Hot Takes",
    "# Things We Don't Talk About", "# Trend Filters"
]
VISUAL_SECTIONS = [
    "# Palette", "# Typography", "# Layout",
    "# Vibe Rules", "# Output sizes"
]
VOICE_FRONTMATTER = ["brand", "extracted-from", "extracted-on", "sample-count"]
PERSPECTIVE_FRONTMATTER = ["brand", "extracted-from", "last-updated"]
VISUAL_FRONTMATTER = ["brand", "last-updated"]


def parse_frontmatter(content: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return {}
    keys = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            keys[k.strip()] = v.strip()
    return keys


def validate_file(path: str, required_sections: list, required_fm: list) -> list:
    errors = []
    if not os.path.isfile(path):
        return [f"missing file: {path}"]
    content = open(path).read()
    fm = parse_frontmatter(content)
    for k in required_fm:
        if k not in fm:
            errors.append(f"{os.path.basename(path)}: missing frontmatter key '{k}'")
    for s in required_sections:
        if s not in content:
            errors.append(f"{os.path.basename(path)}: missing section '{s}'")
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand-dir", required=True)
    args = ap.parse_args()

    bd = args.brand_dir
    all_errors = []
    all_errors += validate_file(os.path.join(bd, "brand-voice.md"), VOICE_SECTIONS, VOICE_FRONTMATTER)
    all_errors += validate_file(os.path.join(bd, "brand-perspective.md"), PERSPECTIVE_SECTIONS, PERSPECTIVE_FRONTMATTER)
    all_errors += validate_file(os.path.join(bd, "visual-system.md"), VISUAL_SECTIONS, VISUAL_FRONTMATTER)

    if all_errors:
        for e in all_errors:
            print(f"[FAIL] {e}")
        sys.exit(1)
    print(f"[PASS] {bd}: brand DNA valid")


if __name__ == "__main__":
    main()
