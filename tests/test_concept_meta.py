"""Tests for lib/concept_meta.py."""

import json
import os

import pytest

from lib.concept_meta import (
    CONCEPT_META_SCHEMA_VERSION,
    REQUIRED_FIELDS,
    read_meta,
    write_meta,
)


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "concept_meta")


def _valid_meta() -> dict:
    return {
        "format": "numbered_diagnostic",
        "close_action": "save",
        "hook_pattern": "observation",
        "hook_score": 47,
        "concept_score": 8.7,
        "claims_personal_fact": False,
        "concept_id": "concept_3",
        "brand": "matt",
        "timestamp": "2026-05-12T14:30:00Z",
    }


def test_write_meta_creates_file_with_schema_version(tmp_path):
    path = write_meta(str(tmp_path), _valid_meta())
    assert path.endswith("concept-meta.json")
    parsed = json.loads(open(path).read())
    assert parsed["_schema_version"] == CONCEPT_META_SCHEMA_VERSION


def test_read_meta_round_trips(tmp_path):
    write_meta(str(tmp_path), _valid_meta())
    parsed = read_meta(str(tmp_path))
    assert parsed["concept_id"] == "concept_3"
    assert parsed["claims_personal_fact"] is False


def test_required_fields_match_spec():
    expected = {
        "format", "close_action", "hook_pattern", "hook_score",
        "concept_score", "claims_personal_fact", "concept_id",
        "brand", "timestamp",
    }
    assert REQUIRED_FIELDS == expected


def test_missing_required_field_raises(tmp_path):
    bad = _valid_meta()
    del bad["concept_id"]
    with pytest.raises(ValueError, match="concept_id"):
        write_meta(str(tmp_path), bad)


def test_extra_fields_preserved_on_round_trip(tmp_path):
    meta = _valid_meta()
    meta["extra_field"] = "extra_value"
    write_meta(str(tmp_path), meta)
    parsed = read_meta(str(tmp_path))
    assert parsed["extra_field"] == "extra_value"


def test_read_nonexistent_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_meta(str(tmp_path))


def test_write_meta_emits_schema_version_2(tmp_path):
    meta = {
        "format": "numbered_diagnostic",
        "close_action": "save",
        "hook_pattern": "observation",
        "hook_score": 47,
        "concept_score": 8.7,
        "claims_personal_fact": False,
        "concept_id": "concept_1",
        "brand": "matt",
        "timestamp": "2026-05-12T14:30:00Z",
        "save_filter_skipped": False,
        "visual_hook": "matt at desk, late evening lamp.",
        "scene_direction_source": "stage_3",
        "word_cap_overridden": True,
        "word_cap_source_path": "brands/matt/styles/social_native/style.yaml",
    }
    write_meta(str(tmp_path), meta)
    out = read_meta(str(tmp_path))
    assert out["_schema_version"] == 2
    assert out["visual_hook"] == "matt at desk, late evening lamp."
    assert out["scene_direction_source"] == "stage_3"
    assert out["word_cap_overridden"] is True


def test_read_meta_tolerates_v1_record():
    fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures", "concept_meta")
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp()
    try:
        shutil.copy(
            os.path.join(fixture_dir, "v1_meta.json"),
            os.path.join(tmp, "concept-meta.json"),
        )
        out = read_meta(tmp)
        assert out["_schema_version"] == 1
        assert out["format"] == "numbered_diagnostic"
        assert out.get("visual_hook") in (None, "")
        assert out.get("scene_direction_source") in (None, "")
        assert out.get("word_cap_overridden") in (None, False)
    finally:
        shutil.rmtree(tmp)


def test_write_meta_rejects_invalid_scene_direction_source(tmp_path):
    meta = {
        "format": "narrative",
        "close_action": "save",
        "hook_pattern": "observation",
        "hook_score": 30,
        "concept_score": 7.0,
        "claims_personal_fact": False,
        "concept_id": "x",
        "brand": "matt",
        "timestamp": "2026-05-12T14:30:00Z",
        "save_filter_skipped": False,
        "scene_direction_source": "bogus",
    }
    with pytest.raises(ValueError, match="scene_direction_source"):
        write_meta(str(tmp_path), meta)
