"""Verify workflows/onboard-brand.md has all required sections and references."""
import os
import re

KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(KIT_ROOT, "workflows", "onboard-brand.md")


def _read():
    with open(WORKFLOW) as f:
        return f.read()


def test_workflow_exists():
    assert os.path.isfile(WORKFLOW)


def test_workflow_has_paste_and_interview_modes():
    text = _read()
    assert re.search(r"^## Path A: Paste mode", text, re.MULTILINE)
    assert re.search(r"^## Path B: Interview mode", text, re.MULTILINE)


def test_workflow_references_voice_extraction_rubric():
    text = _read()
    assert "voice-extraction-rubric.md" in text


def test_workflow_calls_init_brand():
    text = _read()
    assert "init_brand.sh" in text


def test_workflow_calls_validator():
    text = _read()
    assert "validate_brand.py" in text


def test_workflow_calls_doctor():
    text = _read()
    assert "doctor.sh" in text


def test_workflow_includes_perspective_extractor_subflow():
    text = _read()
    assert re.search(r"perspective extractor", text, re.IGNORECASE)
    # Hot takes format
    assert re.search(r"Most people think X\. We think Y because Z", text)


def test_workflow_drafts_default_character_for_snc():
    text = _read()
    assert "character-default.md" in text
    assert re.search(r"social-native|candid-person", text)


def test_workflow_emits_three_required_dna_files():
    text = _read()
    for f in ["brand-voice.md", "brand-perspective.md", "visual-system.md"]:
        assert f in text, f"workflow missing reference to {f}"


def test_workflow_has_no_fabrication_rule():
    text = _read()
    assert re.search(r"no fabrication", text, re.IGNORECASE)
    assert "<TODO" in text  # placeholder convention is documented
