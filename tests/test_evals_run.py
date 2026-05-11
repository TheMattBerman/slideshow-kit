import json
import os
import shutil
import subprocess
import sys


KIT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EVALS_DIR = os.path.join(KIT_DIR, "evals")
RUN_PY = os.path.join(EVALS_DIR, "run.py")
OUTPUT_DIR = os.path.join(EVALS_DIR, "output")


def setup_function(_):
    if os.path.isdir(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)


def test_run_py_exits_zero_on_fixtures():
    result = subprocess.run(
        [sys.executable, RUN_PY],
        capture_output=True,
        text=True,
        cwd=KIT_DIR,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"


def test_run_py_writes_into_output_dir_only():
    subprocess.run([sys.executable, RUN_PY], capture_output=True, text=True, cwd=KIT_DIR)
    assert os.path.isdir(OUTPUT_DIR)
    # No writes outside evals/output/. Spot-check that brand workspaces were not touched.
    # Harness must not write into the kit's real brand workspace dirs.
    fake_brand = os.path.join(KIT_DIR, "brands", "fixture")
    assert not os.path.exists(fake_brand), f"run.py wrote to {fake_brand} (must stay in evals/output/)"


def test_run_py_produces_summary_json():
    subprocess.run([sys.executable, RUN_PY], capture_output=True, text=True, cwd=KIT_DIR)
    summary_path = os.path.join(OUTPUT_DIR, "summary.json")
    assert os.path.isfile(summary_path)
    with open(summary_path) as f:
        summary = json.load(f)
    assert summary["status"] == "ok"
    for stage in [
        "load_brand_dna",
        "filter_trends",
        "apply_voice_lens",
        "build_branded_script",
        "build_social_native_script",
        "publish_dry_run",
        "log_run",
    ]:
        assert stage in summary["stages"], f"missing stage: {stage}"
        assert summary["stages"][stage]["status"] == "pass", f"{stage} did not pass: {summary['stages'][stage]}"


def test_run_py_makes_no_network_calls():
    # Smoke check: harness must not import requests/openai or call urllib in default code path.
    # We assert by inspecting the run output for a known marker that says "no-network mode confirmed".
    result = subprocess.run([sys.executable, RUN_PY], capture_output=True, text=True, cwd=KIT_DIR)
    assert "[eval] no-network mode" in result.stdout


def test_dry_run_payload_includes_style_field():
    """v0.6.0: each post payload carries a style field."""
    subprocess.run([sys.executable, RUN_PY], capture_output=True, text=True, cwd=KIT_DIR)
    posts_dir = os.path.join(OUTPUT_DIR, "posts")
    post_path = os.path.join(posts_dir, "post-01.json")
    assert os.path.isfile(post_path), f"expected post-01.json at {post_path}"
    with open(post_path) as f:
        payload = json.load(f)
    assert "style" in payload, "payload missing 'style' field"
    assert payload["style"] == "eval_fixture_style"


def test_dry_run_images_have_flat_style_prefix():
    """v0.6.0: image filenames are flat with style prefix."""
    subprocess.run([sys.executable, RUN_PY], capture_output=True, text=True, cwd=KIT_DIR)
    posts_dir = os.path.join(OUTPUT_DIR, "posts")
    post_path = os.path.join(posts_dir, "post-01.json")
    assert os.path.isfile(post_path), f"expected post-01.json at {post_path}"
    with open(post_path) as f:
        payload = json.load(f)
    for img in payload["images"]:
        assert img.startswith("eval_fixture_style-slide-"), (
            f"image filename '{img}' does not start with 'eval_fixture_style-slide-'"
        )
