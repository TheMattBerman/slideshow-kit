import sys, os, json, subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "styled-carousel", "scripts"))
import generate_styled_carousel as gsc  # type: ignore[reportMissingImports]


def setup_brand(brands_root, slug="testbrand"):
    bd = os.path.join(brands_root, slug)
    os.makedirs(bd, exist_ok=True)
    voice = "---\nbrand: " + slug + "\nextracted-from: manual\nextracted-on: 2026-05-03\nsample-count: 0\n---\n\n"
    voice += "\n\n".join(f"{s}\nstub\n" for s in [
        "# Voice Principles", "# Structure", "# Signature Patterns", "# What NOT to Do", "# Length / Format"
    ])
    open(os.path.join(bd, "brand-voice.md"), "w").write(voice)
    persp = "---\nbrand: " + slug + "\nextracted-from: manual\nlast-updated: 2026-05-03\n---\n\n"
    persp += "\n\n".join(f"{s}\nstub\n" for s in [
        "# ICP", "# Pillars", "# Hot Takes", "# Things We Don't Talk About", "# Trend Filters"
    ])
    open(os.path.join(bd, "brand-perspective.md"), "w").write(persp)
    visual = """---
brand: """ + slug + """
last-updated: 2026-05-03
---

# Palette
- Background: `#0D1117`
- Primary accent: `#F43F5E`
- Secondary accent: `#FACC15`
- Neutral: `#94A3B8`

# Typography
- Headline weight: extra-bold
- Headline case: UPPERCASE
- Body weight: regular
- Body case: Sentence case
- Pull-quote treatment: italic

# Layout
- Slide arc: HOOK -> REVEAL -> SETUP -> EXAMPLES -> OUTCOME -> CTA
- Negative space: generous
- Icon style: none

# Vibe Rules
- Tone: minimal
- Avoid: stock photos, gradients

# Output sizes
- LinkedIn carousel: 1024x1536
- Feed: 1024x1024
"""
    open(os.path.join(bd, "visual-system.md"), "w").write(visual)
    return bd


def write_style(brand_dir, style_name, design_md):
    style_dir = os.path.join(brand_dir, "styles", style_name)
    os.makedirs(style_dir, exist_ok=True)
    open(os.path.join(style_dir, "DESIGN.md"), "w").write(design_md)
    return style_dir


def test_dry_run_emits_prompts_and_log(tmp_path):
    brands_root = tmp_path / "brands"
    setup_brand(str(brands_root))
    out = tmp_path / "out"
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(repo_root, "examples", "test-script.md")
    r = subprocess.run([
        "python3",
        os.path.join(repo_root, "skills", "styled-carousel", "scripts", "generate_styled_carousel.py"),
        "--brand", "testbrand",
        "--script", script,
        "--output", str(out),
        "--brands-root", str(brands_root),
        "--no-format-check",
        "--dry-run",
    ], capture_output=True, text=True, env={**os.environ, "HOME": str(tmp_path), "SLIDESHOW_BRANDS_ROOT": str(brands_root)})
    assert r.returncode == 0, r.stderr

    assert (out / "prompts.json").exists()
    assert (out / "output-log.json").exists()
    log = json.loads((out / "output-log.json").read_text())
    assert log["brand"] == "testbrand"
    assert log["dry_run"] is True
    # TODO: rewrite for v0.6.0 token-resolved prompt assembly
    # Old assertion: assert len(log["slides"]) >= 6
    # New log shape: log["slides"] is an integer count, not a list.
    assert log["slides"] >= 6


def test_default_size_resolves_from_style_aspect_ratio(tmp_path):
    brands_root = tmp_path / "brands"
    brand_dir = setup_brand(str(brands_root))
    write_style(brand_dir, "iphone_candid", """---
name: iphone_candid
extends: brand
aspect_ratio: "9:16"
image_treatment: "iphone_candid"
---

# Style: iPhone Candid

Use candid phone-style photography.
""")
    out = tmp_path / "out"
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(repo_root, "examples", "test-script.md")
    r = subprocess.run([
        "python3",
        os.path.join(repo_root, "skills", "styled-carousel", "scripts", "generate_styled_carousel.py"),
        "--brand", "testbrand",
        "--style", "iphone_candid",
        "--script", script,
        "--output", str(out),
        "--brands-root", str(brands_root),
        "--no-format-check",
        "--no-visual-director",
        "--dry-run",
    ], capture_output=True, text=True, env={**os.environ, "HOME": str(tmp_path), "SLIDESHOW_BRANDS_ROOT": str(brands_root)})
    assert r.returncode == 0, r.stderr

    log = json.loads((out / "output-log.json").read_text())
    assert log["sizes"] == ["768x1344"]


def test_auto_provider_uses_codex_native_in_codex_desktop(monkeypatch):
    monkeypatch.setenv("CODEX_INTERNAL_ORIGINATOR_OVERRIDE", "Codex Desktop")
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-123")
    monkeypatch.setenv("CODEX_SHELL", "1")
    assert gsc.resolve_generation_provider("auto", dry_run=False) == "codex-native"
    assert gsc.resolve_generation_provider("api", dry_run=False) == "api"
    assert gsc.resolve_generation_provider("auto", dry_run=True) == "dry-run"


def test_codex_native_provider_writes_handoff_manifest_without_api(tmp_path):
    brands_root = tmp_path / "brands"
    setup_brand(str(brands_root))
    out = tmp_path / "out"
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(repo_root, "examples", "test-script.md")
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "SLIDESHOW_BRANDS_ROOT": str(brands_root),
        "CODEX_INTERNAL_ORIGINATOR_OVERRIDE": "Codex Desktop",
        "CODEX_THREAD_ID": "thread-123",
        "CODEX_SHELL": "1",
    }
    env.pop("OPENAI_API_KEY", None)
    r = subprocess.run([
        "python3",
        os.path.join(repo_root, "skills", "styled-carousel", "scripts", "generate_styled_carousel.py"),
        "--brand", "testbrand",
        "--script", script,
        "--output", str(out),
        "--brands-root", str(brands_root),
        "--no-format-check",
        "--no-visual-director",
    ], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr

    manifest = json.loads((out / "native-generation-requests.json").read_text())
    assert manifest["provider"] == "codex-native"
    assert len(manifest["requests"]) >= 1
    first = manifest["requests"][0]
    assert first["output_path"].endswith(".png")
    assert first["prompt"]

    log = json.loads((out / "output-log.json").read_text())
    assert log["generation_provider"] == "codex-native"
    assert log["native_generation_requests"] == "native-generation-requests.json"
    assert log["slides_requested"] == len(manifest["requests"])
    assert log["slides_completed"] == 0
    assert all(r["status"] == "pending_codex_native" for r in log["slide_results"])


def test_fails_on_missing_brand(tmp_path):
    brands_root = tmp_path / "brands"
    brands_root.mkdir()
    out = tmp_path / "out"
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script = os.path.join(repo_root, "examples", "test-script.md")
    r = subprocess.run([
        "python3",
        os.path.join(repo_root, "skills", "styled-carousel", "scripts", "generate_styled_carousel.py"),
        "--brand", "nonexistent",
        "--script", script,
        "--output", str(out),
        "--brands-root", str(brands_root),
        "--dry-run",
    ], capture_output=True, text=True, env={**os.environ, "HOME": str(tmp_path), "SLIDESHOW_BRANDS_ROOT": str(brands_root)})
    assert r.returncode == 1
    assert "brand" in (r.stderr + r.stdout).lower()
