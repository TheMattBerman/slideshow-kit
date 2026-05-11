#!/usr/bin/env python3
"""Diagnostic-only face-similarity scorer (delegates to production module).

The production scorer lives at:
  skills/social-native-carousel/scripts/score_face_similarity.py

This file exists for the original Phase 0 diagnostic CLI surface
(`--dir <path>` repeatable, `--output <json>`).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(
    HERE, "..", "..", "skills", "social-native-carousel", "scripts"
))
import score_face_similarity as _sfs  # type: ignore[reportMissingImports]

cosine = _sfs.cosine
mean_pair_scores = _sfs.mean_pair_scores
compare_pair = _sfs.compare_pair
score_directory = _sfs.score_directory
MODEL = _sfs.MODEL
import subprocess  # noqa: E402 -- re-export for test monkeypatching


def _openai_key() -> str:
    k = os.environ.get("OPENAI_API_KEY")
    if not k:
        raise SystemExit("OPENAI_API_KEY required")
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, action="append",
                    help="slide directory; pass multiple to score variants side-by-side")
    ap.add_argument("--output", required=True, help="path to write scores JSON")
    args = ap.parse_args()
    api_key = _openai_key()

    results = {"variants": {}, "model": MODEL}
    for d in args.dir:
        name = os.path.basename(os.path.abspath(d))
        print(f"[SCORE] {name}", file=sys.stderr)
        results["variants"][name] = score_directory(d, api_key)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print("\nVariant     | Mean score | Slides")
    print("------------|------------|-------")
    for name, r in results["variants"].items():
        m = r.get("mean_score")
        m_str = f"{m:.3f}" if m is not None else "n/a"
        print(f"{name:<11} | {m_str:>10} | {r['count']}")


if __name__ == "__main__":
    main()
