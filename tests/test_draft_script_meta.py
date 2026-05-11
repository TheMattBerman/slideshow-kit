"""Tests for lib/draft_script_meta.py."""

import json

import pytest

from lib.draft_script_meta import (
    ConceptFields,
    Flags,
    _run_lint_chain,
    build_meta,
    extract_concept_fields,
    main,
    write_dry_run_artifacts,
)


SAMPLE_PICK_TEXT = """
# Picked concept (mode: interactive)

## Concept 1 (rank: 1, concept_score: 8.7, claims_personal_fact: false)

**Format:** numbered_diagnostic
**Close action:** save
**Arc:** the four tells.
**Visual hook:** matt at desk, late evening lamp warmth.
**Why this works:** placeholder.

### Hook variants
1. (observation, shock 47) "scroll your feed."
"""


def test_extract_concept_fields_happy_path():
    fields = extract_concept_fields(SAMPLE_PICK_TEXT)
    assert fields.fmt == "numbered_diagnostic"
    assert fields.close_action == "save"
    assert fields.concept_n == "1"
    assert fields.concept_score == 8.7
    assert fields.claims_personal_fact is False
    assert fields.hook_pattern == "observation"
    assert fields.hook_score == 47
    assert fields.visual_hook == "matt at desk, late evening lamp warmth."
    assert fields.concept_arc == "the four tells."


def test_extract_concept_fields_missing_visual_hook():
    text = SAMPLE_PICK_TEXT.replace(
        "**Visual hook:** matt at desk, late evening lamp warmth.", ""
    )
    fields = extract_concept_fields(text)
    assert fields.visual_hook == ""


def test_extract_concept_fields_missing_claims_personal_defaults_false():
    text = """## Concept 5 (rank: 5, concept_score: 6.0)

**Format:** narrative
**Close action:** save

### Hook variants
1. (observation, shock 30) "h."
"""
    fields = extract_concept_fields(text)
    assert fields.claims_personal_fact is False


def test_extract_concept_fields_claims_personal_true():
    text = SAMPLE_PICK_TEXT.replace(
        "claims_personal_fact: false", "claims_personal_fact: true"
    )
    fields = extract_concept_fields(text)
    assert fields.claims_personal_fact is True


def test_extract_concept_fields_missing_hook_variants_defaults():
    text = """## Concept 1 (rank: 1, concept_score: 5.0, claims_personal_fact: false)
**Format:** narrative
**Close action:** save
"""
    fields = extract_concept_fields(text)
    assert fields.hook_pattern == "single_claim"
    assert fields.hook_score == 0


def test_build_meta_includes_v2_fields():
    fields = extract_concept_fields(SAMPLE_PICK_TEXT)
    flags = Flags(no_save_filter=False)
    meta = build_meta(fields, brand="matt", flags=flags)
    # _schema_version is added by write_meta, not build_meta.
    assert "_schema_version" not in meta
    assert meta["format"] == "numbered_diagnostic"
    assert meta["concept_id"] == "concept_1"
    assert meta["visual_hook"] == "matt at desk, late evening lamp warmth."
    assert meta["scene_direction_source"] == "stage_3"
    assert meta["save_filter_skipped"] is False


def test_build_meta_records_skip_flags():
    fields = extract_concept_fields(SAMPLE_PICK_TEXT)
    flags = Flags(no_lint=True, no_format_check=True, no_save_filter=True)
    meta = build_meta(fields, brand="matt", flags=flags)
    assert meta["lint_skipped"] is True
    assert meta["format_check_skipped"] is True
    assert meta["save_filter_skipped"] is True


def test_write_dry_run_artifacts_writes_three_files(tmp_path):
    fields = extract_concept_fields(SAMPLE_PICK_TEXT)
    flags = Flags(dry_run=True)
    write_dry_run_artifacts(str(tmp_path), fields, brand="matt", flags=flags)

    assert (tmp_path / "script.md").is_file()
    assert (tmp_path / "scene-direction.md").is_file()
    assert (tmp_path / "concept-meta.json").is_file()

    script_text = (tmp_path / "script.md").read_text(encoding="utf-8")
    assert "format: numbered_diagnostic" in script_text
    assert "# HOOK" in script_text

    scene_text = (tmp_path / "scene-direction.md").read_text(encoding="utf-8")
    assert "source: stage_3" in scene_text
    assert "matt at desk" in scene_text  # visual_hook propagates

    meta = json.loads((tmp_path / "concept-meta.json").read_text(encoding="utf-8"))
    assert meta["_schema_version"] == 2
    assert meta["scene_direction_source"] == "stage_3"


def test_main_non_dry_run_writes_scene_direction_before_meta(
    tmp_path, monkeypatch
):
    (tmp_path / "concept-pick.md").write_text(SAMPLE_PICK_TEXT, encoding="utf-8")
    (tmp_path / "concept-context.json").write_text(
        json.dumps({"brand": "matt"}), encoding="utf-8"
    )
    (tmp_path / "script.md").write_text(
        "---\nformat: numbered_diagnostic\nclose_action: save\n---\n"
        "# HOOK\n"
        "the four tells of every AI carousel. once you see them you cant unsee.\n"
        "# TELL #1\n"
        "tell #1: 6 slides. always 6. real carousels are sized to the story.\n"
        "# TELL #2\n"
        "tell #2: stock backgrounds. nobody's brand actually looks like that.\n"
        "# TELL #3\n"
        "tell #3: slide 4 always says nothing. the model could not think.\n"
        "# TELL #4\n"
        "tell #4: it ends on a quote. the model could not write an ending.\n"
        "# FIX\n"
        "the fix is structural. ask 3 questions before you ship the next one.\n"
        "# CTA\n"
        "save this. run the 3-question audit before your next 3 posts.\n",
        encoding="utf-8",
    )

    brands_root = tmp_path / "brands"
    brand_dir = brands_root / "matt"
    brand_dir.mkdir(parents=True)
    (brand_dir / "visual-system.md").write_text(
        "DESIGN body content", encoding="utf-8"
    )
    monkeypatch.setenv("SLIDESHOW_BRANDS_ROOT", str(brands_root))

    captured_user_messages = []

    def fake_call(_system_msg, user_msg, _api_key, _model):
        captured_user_messages.append(user_msg)
        return json.dumps([
            {
                "slide_idx": idx,
                "visual": f"matt at desk under lamp light, scene {idx}.",
                "tone": "observational",
                "rationale": "matches slide",
            }
            for idx in range(7)
        ])

    def fake_write_meta(run_dir, meta):
        assert (tmp_path / "scene-direction.md").is_file()
        assert meta["scene_direction_source"] == "stage_3"

    monkeypatch.setattr("lib.visual_director._call_openai", fake_call)
    monkeypatch.setattr("lib.draft_script_meta.write_meta", fake_write_meta)

    rc = main([
        "--run-dir",
        str(tmp_path),
        "--no-lint",
        "--no-format-check",
        "--no-save-filter",
    ])

    assert rc == 0
    scene_text = (tmp_path / "scene-direction.md").read_text(encoding="utf-8")
    assert "source: stage_3" in scene_text
    assert "matt at desk" in scene_text
    assert "Visual hook: matt at desk, late evening lamp warmth." in captured_user_messages[0]
    assert "Concept arc: the four tells." in captured_user_messages[0]


def test_main_non_dry_run_keeps_meta_when_direct_scenes_fails(
    tmp_path, monkeypatch
):
    (tmp_path / "concept-pick.md").write_text(SAMPLE_PICK_TEXT, encoding="utf-8")
    (tmp_path / "concept-context.json").write_text(
        json.dumps({"brand": "matt"}), encoding="utf-8"
    )
    (tmp_path / "script.md").write_text(
        "---\nformat: narrative\nclose_action: save\n---\n"
        "# HOOK\n"
        "the four tells of every AI carousel. once you see them.\n"
        "# BODY\n"
        "dated tuesday, 12 posts had the same blank middle and one generic quote.\n"
        "# CTA\n"
        "save this audit before you draft the next carousel.\n",
        encoding="utf-8",
    )

    def fake_call(*_args, **_kwargs):
        raise ValueError("missing key")

    monkeypatch.setattr("lib.visual_director._call_openai", fake_call)

    rc = main([
        "--run-dir",
        str(tmp_path),
        "--no-lint",
        "--no-format-check",
        "--no-save-filter",
    ])

    assert rc == 0
    scene_text = (tmp_path / "scene-direction.md").read_text(encoding="utf-8")
    assert "source: stage_3" in scene_text
    assert "matt at desk, late evening lamp warmth" in scene_text
    meta = json.loads((tmp_path / "concept-meta.json").read_text(encoding="utf-8"))
    assert meta["scene_direction_source"] == "stage_3"


def test_format_aware_placeholder_narrative_scaffold(tmp_path):
    """Non-numbered_diagnostic formats get a HOOK/BODY/CTA scaffold."""
    text = SAMPLE_PICK_TEXT.replace(
        "**Format:** numbered_diagnostic", "**Format:** narrative"
    )
    fields = extract_concept_fields(text)
    flags = Flags(dry_run=True)
    write_dry_run_artifacts(str(tmp_path), fields, brand="matt", flags=flags)
    script_text = (tmp_path / "script.md").read_text(encoding="utf-8")
    assert "format: narrative" in script_text
    assert "# BODY" in script_text
    assert "# TELL" not in script_text


def test_run_lint_chain_passes_clean_script_with_all_bypass(tmp_path):
    """All bypass flags on -> lint chain is a no-op and returns 0."""
    fields = ConceptFields(
        fmt="numbered_diagnostic",
        close_action="save",
        concept_n="1",
        concept_score=8.7,
        claims_personal_fact=False,
        hook_pattern="observation",
        hook_score=47,
        visual_hook="",
    )
    flags = Flags(no_save_filter=True, no_lint=True, no_format_check=True)
    script_md = tmp_path / "script.md"
    script_md.write_text(
        "---\nformat: numbered_diagnostic\nclose_action: save\n---\n# HOOK\nx\n"
    )
    rc = _run_lint_chain(str(tmp_path), fields, flags)
    assert rc == 0


def test_run_lint_chain_missing_script_md_returns_1(tmp_path):
    fields = ConceptFields(
        fmt="narrative",
        close_action="save",
        concept_n="1",
        concept_score=5.0,
        claims_personal_fact=False,
        hook_pattern="single_claim",
        hook_score=0,
        visual_hook="",
    )
    flags = Flags(no_lint=True, no_format_check=True, no_save_filter=True)
    rc = _run_lint_chain(str(tmp_path), fields, flags)
    assert rc == 1


def test_run_lint_chain_save_filter_catches_thin_body(tmp_path):
    """A body with no save-worthy markers triggers save_filter violation."""
    fields = ConceptFields(
        fmt="narrative",
        close_action="save",
        concept_n="1",
        concept_score=5.0,
        claims_personal_fact=False,
        hook_pattern="single_claim",
        hook_score=0,
        visual_hook="",
    )
    flags = Flags(no_lint=True, no_format_check=True, no_save_filter=False)
    # Bypass voice + format lint; only save_filter active. Body has no
    # numbers, dates, quotes, or framework markers.
    script_md = tmp_path / "script.md"
    script_md.write_text(
        "---\nformat: narrative\nclose_action: save\n---\n"
        "# HOOK\nopener line.\n\n"
        "# BODY\nthis is generic prose with nothing specific in it whatsoever.\n\n"
        "# CTA\nsave this.\n"
    )
    rc = _run_lint_chain(str(tmp_path), fields, flags)
    assert rc == 1


def test_split_script_handles_numbered_diagnostic_multi_token_headings():
    """Headings like `# TELL #1` must split correctly so save_filter sees per-slot bodies."""
    from lib.draft_script_meta import _split_script_into_slides
    script = (
        "---\nformat: numbered_diagnostic\nclose_action: save\n---\n"
        "# HOOK\n"
        "the four tells of every AI carousel.\n"
        "# TELL #1\n"
        "tell #1: 6 slides. always 6.\n"
        "# TELL #2\n"
        "tell #2: stock backgrounds.\n"
        "# FIX\n"
        "the fix is structural.\n"
        "# CTA\n"
        "save this audit.\n"
    )
    sections = _split_script_into_slides(script)
    roles = [r for r, _ in sections]
    assert roles == ["HOOK", "TELL", "TELL", "FIX", "CTA"], roles
    # Each TELL body must be the per-slot text, not a joined blob.
    tell_bodies = [b for r, b in sections if r == "TELL"]
    assert "6 slides" in tell_bodies[0]
    assert "stock backgrounds" in tell_bodies[1]
    assert "stock backgrounds" not in tell_bodies[0]


def test_run_lint_chain_save_filter_catches_thin_numbered_diagnostic_body(tmp_path):
    """Regression for C1: thin TELL bodies must produce save_filter violations
    (would silently pass under the old re.split splitter)."""
    from lib.draft_script_meta import _run_lint_chain, ConceptFields, Flags
    fields = ConceptFields(
        fmt="numbered_diagnostic",
        close_action="save",
        concept_n="1",
        concept_score=8.0,
        claims_personal_fact=False,
        hook_pattern="observation",
        hook_score=40,
        visual_hook="",
    )
    # Build a script with bodies that would WOULD-fail save_filter under standard rules
    # (cap > 12 means standard slots; need >= 2 marker categories to pass).
    script_md = tmp_path / "script.md"
    script_md.write_text(
        "---\nformat: numbered_diagnostic\nclose_action: save\n---\n"
        "# HOOK\n"
        "scroll your feed and you can see them.\n"
        "# TELL #1\n"
        "this body is generic prose without any of the markers we need.\n"
        "# TELL #2\n"
        "another generic body that also fails the save heuristic.\n"
        "# TELL #3\n"
        "yet another thin body without specifics.\n"
        "# TELL #4\n"
        "final thin body and still no markers.\n"
        "# FIX\n"
        "the fix is structural review.\n"
        "# CTA\n"
        "save this audit for later.\n"
    )
    flags = Flags(
        no_lint=True,         # bypass voice_lint
        no_format_check=True, # bypass format_lint
        no_save_filter=False, # keep save_filter ACTIVE
    )
    rc = _run_lint_chain(str(tmp_path), fields, flags)
    # save_filter should fail at least one TELL body (zero markers, standard cap).
    assert rc != 0, "save_filter must catch thin TELL bodies in numbered_diagnostic format"


def test_resolve_effective_word_cap_uses_format_registry():
    """C2 regression: cap is per-slot from format YAML, not hardcoded 50.

    Uses counter_narrative/THE_QUESTION (word_count_range [10, 30]) to verify
    the cap is genuinely different from the old hardcoded 50.
    """
    from lib.draft_script_meta import _resolve_effective_word_cap, Flags
    cap = _resolve_effective_word_cap("counter_narrative", "THE_QUESTION", "/tmp", Flags())
    assert cap != 50, f"expected per-slot cap from format registry; got hardcoded 50"
    assert cap == 30, f"counter_narrative THE_QUESTION cap should be 30, got {cap}"
    assert isinstance(cap, int) and cap > 0


def test_resolve_effective_word_cap_resolves_alias_to_canonical_slot():
    """Heading token 'TELL' must resolve to canonical 'ITEM' slot via aliases."""
    from lib.draft_script_meta import _resolve_effective_word_cap, Flags
    cap_tell = _resolve_effective_word_cap("numbered_diagnostic", "TELL", "/tmp", Flags())
    cap_item = _resolve_effective_word_cap("numbered_diagnostic", "ITEM", "/tmp", Flags())
    # Both should resolve to the same slot (ITEM) -> same cap.
    assert cap_tell == cap_item == 50


def test_resolve_effective_word_cap_falls_back_when_unknown_format():
    """Unknown format name returns the safe default 50."""
    from lib.draft_script_meta import _resolve_effective_word_cap, Flags
    cap = _resolve_effective_word_cap("nonexistent_format", "ANY", "/tmp", Flags())
    assert cap == 50
