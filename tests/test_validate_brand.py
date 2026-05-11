import subprocess
import os

REQUIRED_VOICE_SECTIONS = [
    "# Voice Principles", "# Structure", "# Signature Patterns",
    "# What NOT to Do", "# Length / Format"
]
REQUIRED_PERSPECTIVE_SECTIONS = [
    "# ICP", "# Pillars", "# Hot Takes",
    "# Things We Don't Talk About", "# Trend Filters"
]
REQUIRED_VISUAL_SECTIONS = [
    "# Palette", "# Typography", "# Layout",
    "# Vibe Rules", "# Output sizes"
]


def write_complete_brand(brand_dir):
    voice = "---\nbrand: test\nextracted-from: manual\nextracted-on: 2026-05-03\nsample-count: 0\n---\n\n"
    voice += "\n\n".join(f"{s}\nstub\n" for s in REQUIRED_VOICE_SECTIONS)
    persp = "---\nbrand: test\nextracted-from: manual\nlast-updated: 2026-05-03\n---\n\n"
    persp += "\n\n".join(f"{s}\nstub\n" for s in REQUIRED_PERSPECTIVE_SECTIONS)
    vis = "---\nbrand: test\nlast-updated: 2026-05-03\n---\n\n"
    vis += "\n\n".join(f"{s}\nstub\n" for s in REQUIRED_VISUAL_SECTIONS)
    open(os.path.join(brand_dir, "brand-voice.md"), "w").write(voice)
    open(os.path.join(brand_dir, "brand-perspective.md"), "w").write(persp)
    open(os.path.join(brand_dir, "visual-system.md"), "w").write(vis)


def run_validator(brand_dir):
    return subprocess.run(
        ["python3", "scripts/validate_brand.py", "--brand-dir", brand_dir],
        capture_output=True, text=True
    )


def test_validator_passes_on_complete_brand(tmp_path):
    write_complete_brand(str(tmp_path))
    r = run_validator(str(tmp_path))
    assert r.returncode == 0, r.stderr


def test_validator_fails_on_missing_voice_section(tmp_path):
    write_complete_brand(str(tmp_path))
    voice_path = tmp_path / "brand-voice.md"
    content = voice_path.read_text().replace("# Voice Principles", "# Voice Principle")
    voice_path.write_text(content)
    r = run_validator(str(tmp_path))
    assert r.returncode == 1
    assert "Voice Principles" in r.stdout + r.stderr


def test_validator_fails_on_missing_frontmatter_key(tmp_path):
    write_complete_brand(str(tmp_path))
    voice_path = tmp_path / "brand-voice.md"
    content = voice_path.read_text().replace("brand: test\n", "")
    voice_path.write_text(content)
    r = run_validator(str(tmp_path))
    assert r.returncode == 1
    assert "frontmatter" in (r.stdout + r.stderr).lower()


def test_validator_fails_on_missing_file(tmp_path):
    r = run_validator(str(tmp_path))
    assert r.returncode == 1
    assert "missing" in (r.stdout + r.stderr).lower()
