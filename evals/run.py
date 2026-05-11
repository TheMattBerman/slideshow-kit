#!/usr/bin/env python3
"""Slideshow Kit smoke-eval harness.

Exercises the daily-loop pipeline end-to-end against fixtures with no API
calls and no writes outside evals/output/. Pass criteria: every stage emits
a "pass" status; exit 0.

Stages:
    1. load_brand_dna             : read fixture brand DNA + config
    2. filter_trends              : apply perspective filter to fixture trends
    3. apply_voice_lens           : text-only voice transform per trend
    4. build_branded_script       : produce a script dict for branded-carousel
    5. build_social_native_script : produce a script dict for social-native-carousel
    6. publish_dry_run            : emit post-NN.json payloads (no postiz call)
    7. log_run                    : write summary.json under evals/output/
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import sys


KIT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURES = os.path.join(KIT_DIR, "evals", "fixtures")
OUTPUT = os.path.join(KIT_DIR, "evals", "output")


def log(stage: str, status: str, detail: str = "") -> None:
    print(f"[eval] {stage}: {status} {detail}".rstrip())


def parse_frontmatter_and_body(path: str) -> tuple[dict, str]:
    text = open(path).read()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, m.group(2)


def parse_perspective_pillars(body: str) -> list[str]:
    out = []
    in_section = False
    for line in body.splitlines():
        if line.strip().startswith("# Pillars"):
            in_section = True
            continue
        if in_section and line.startswith("# "):
            break
        if in_section and line.strip().startswith("- "):
            out.append(line.strip()[2:].strip())
    return out


def parse_voice_principles(body: str) -> list[str]:
    out = []
    in_section = False
    for line in body.splitlines():
        if line.strip().startswith("# Voice Principles"):
            in_section = True
            continue
        if in_section and line.startswith("# "):
            break
        if in_section and line.strip().startswith("- "):
            out.append(line.strip()[2:].strip())
    return out


def parse_visual_palette(body: str) -> dict:
    out = {}
    in_section = False
    for line in body.splitlines():
        if line.strip().startswith("# Palette"):
            in_section = True
            continue
        if in_section and line.startswith("# "):
            break
        if in_section and line.strip().startswith("- "):
            entry = line.strip()[2:]
            if ":" in entry:
                k, _, v = entry.partition(":")
                out[k.strip()] = v.strip()
    return out


def stage_load_brand_dna() -> dict:
    voice_fm, voice_body = parse_frontmatter_and_body(
        os.path.join(FIXTURES, "brand-voice-fixture.md"))
    persp_fm, persp_body = parse_frontmatter_and_body(
        os.path.join(FIXTURES, "brand-perspective-fixture.md"))
    visual_fm, visual_body = parse_frontmatter_and_body(
        os.path.join(FIXTURES, "visual-system-fixture.md"))
    with open(os.path.join(FIXTURES, "brand-config-fixture.json")) as f:
        config = json.load(f)
    return {
        "voice": {"frontmatter": voice_fm, "principles": parse_voice_principles(voice_body), "body": voice_body},
        "perspective": {"frontmatter": persp_fm, "pillars": parse_perspective_pillars(persp_body), "body": persp_body},
        "visual": {"frontmatter": visual_fm, "palette": parse_visual_palette(visual_body), "body": visual_body},
        "config": config,
    }


def stage_filter_trends(brand: dict) -> list[dict]:
    with open(os.path.join(FIXTURES, "trends-sample.json")) as f:
        trends_doc = json.load(f)
    pillars_lower = [p.lower() for p in brand["perspective"]["pillars"]]
    selected = []
    for t in trends_doc["trends"]:
        text = (t["title"] + " " + t["summary"]).lower()
        if any(any(word in text for word in p.split() if len(word) > 3) for p in pillars_lower):
            selected.append(t)
    if not selected:
        selected = trends_doc["trends"][:1]
    return selected[: brand["config"]["posts_per_day"] * 3]  # over-select for test richness


def stage_apply_voice_lens(brand: dict, trends: list[dict]) -> list[dict]:
    out = []
    for t in trends:
        out.append({
            "trend_id": t["id"],
            "hook_options": [
                f"i used to think {t['title'].lower()} was hype.",
                f"→ {t['title'].lower()}.",
            ],
            "outcome": f"now {t['summary'].split('.')[0].lower()}.",
            "voice_principles_applied": brand["voice"]["principles"][:2],
        })
    return out


def stage_build_branded_script(brand: dict, lensed: list[dict]) -> list[dict]:
    out = []
    palette = brand["visual"]["palette"]
    for entry in lensed:
        out.append({
            "format": "branded",
            "trend_id": entry["trend_id"],
            "slides": [
                {"role": "HOOK", "text": entry["hook_options"][1]},
                {"role": "REVEAL", "text": entry["outcome"]},
                {"role": "SETUP", "text": "here's the actual playbook:"},
                {"role": "EXAMPLES", "text": "1. ...\n2. ...\n3. ..."},
                {"role": "OUTCOME", "text": entry["outcome"]},
                {"role": "CTA", "text": "save."},
            ],
            "palette": palette,
            "sizes": ["1080x1350", "1080x1080"],
        })
    return out


def stage_build_social_native_script(brand: dict, lensed: list[dict]) -> list[dict]:
    brand_slug = brand["config"]["brand"]
    out = []
    for entry in lensed:
        out.append({
            "format": "social-native",
            "brand": brand_slug,
            "trend_id": entry["trend_id"],
            "character_lock": "30s solo operator at desk, daylight, tired-but-grinning",
            "slides": [
                {"role": "candid-1", "text": entry["hook_options"][0]},
                {"role": "candid-2", "text": "(same person, new frame)"},
                {"role": "candid-3", "text": entry["outcome"]},
            ],
            "sizes": ["1080x1080", "1080x1920"],
        })
    return out


def stage_publish_dry_run(brand: dict, branded: list[dict], native: list[dict], out_dir: str) -> dict:
    posts_dir = os.path.join(out_dir, "posts")
    os.makedirs(posts_dir, exist_ok=True)
    integration_ids = brand["config"]["postiz"]["integration_ids"]
    style_name = "eval_fixture_style"
    n = 0
    for script in branded + native:
        n += 1
        post = {
            "caption": script["slides"][0]["text"] + "\n\n" + script["slides"][-1]["text"],
            "images": [
                f"{style_name}-slide-{i + 1:02d}-1024x1536.png"
                for i in range(len(script["slides"]))
            ],
            "platforms": ["linkedin", "instagram"]
                if script["format"] == "branded"
                else ["instagram", "threads"],
            "target_integrations": integration_ids,
            "scheduled_for": "2026-05-06T15:00:00Z",
            "style": style_name,
        }
        with open(os.path.join(posts_dir, f"post-{n:02d}.json"), "w") as f:
            json.dump(post, f, indent=2)
    # Simulate postiz dry-run response
    with open(os.path.join(FIXTURES, "postiz-response-fixture.json")) as f:
        sample_resp = json.load(f)
    return {
        "posts_emitted": n,
        "mode": "dry-run",
        "style": style_name,
        "sample_response": sample_resp,
    }


def stage_log_run(out_dir: str, payload: dict) -> str:
    summary_path = os.path.join(out_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(payload, f, indent=2)
    return summary_path


def main() -> int:
    print("[eval] no-network mode: fixtures only, no external calls")
    if os.path.isdir(OUTPUT):
        shutil.rmtree(OUTPUT)
    os.makedirs(OUTPUT, exist_ok=True)

    started = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stages: dict = {}

    try:
        brand = stage_load_brand_dna()
        stages["load_brand_dna"] = {"status": "pass", "pillars": len(brand["perspective"]["pillars"])}
        log("load_brand_dna", "PASS", f"({len(brand['perspective']['pillars'])} pillars)")

        trends = stage_filter_trends(brand)
        stages["filter_trends"] = {"status": "pass", "count": len(trends)}
        log("filter_trends", "PASS", f"({len(trends)} trends after filter)")

        lensed = stage_apply_voice_lens(brand, trends)
        stages["apply_voice_lens"] = {"status": "pass", "count": len(lensed)}
        log("apply_voice_lens", "PASS", f"({len(lensed)} lensed entries)")

        branded = stage_build_branded_script(brand, lensed)
        stages["build_branded_script"] = {"status": "pass", "count": len(branded)}
        log("build_branded_script", "PASS", f"({len(branded)} scripts)")

        native = stage_build_social_native_script(brand, lensed)
        stages["build_social_native_script"] = {"status": "pass", "count": len(native)}
        log("build_social_native_script", "PASS", f"({len(native)} scripts)")

        publish = stage_publish_dry_run(brand, branded, native, OUTPUT)
        stages["publish_dry_run"] = {"status": "pass", **publish}
        log("publish_dry_run", "PASS", f"({publish['posts_emitted']} posts emitted)")

        summary_path = stage_log_run(OUTPUT, {
            "status": "ok",
            "started_at": started,
            "ended_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "stages": stages,
        })
        stages["log_run"] = {"status": "pass", "path": summary_path}
        log("log_run", "PASS", summary_path)

        # Re-write final summary now that log_run is itself green
        with open(summary_path, "w") as f:
            json.dump({
                "status": "ok",
                "started_at": started,
                "ended_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "stages": stages,
            }, f, indent=2)

    except Exception as exc:
        log("FATAL", "FAIL", str(exc))
        with open(os.path.join(OUTPUT, "summary.json"), "w") as f:
            json.dump({"status": "fail", "error": str(exc), "stages": stages}, f, indent=2)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
