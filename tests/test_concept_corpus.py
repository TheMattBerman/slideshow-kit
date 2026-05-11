"""Tests for lib/concept_corpus.py."""

import os

import pytest

from lib.concept_corpus import CorpusBundle, load_brand_corpus


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "corpus")


def test_rich_brand_loads_all_layers():
    bundle = load_brand_corpus("rich_brand", brands_root=FIXTURES)
    assert isinstance(bundle, CorpusBundle)
    assert "lowercase" in bundle.voice_profile.lower()
    assert "Avoid" in bundle.brand_voice_rules
    assert len(bundle.recent_deliverables) == 5
    assert bundle.is_thin is False


def test_thin_brand_falls_back_to_brand_voice_for_voice_profile():
    bundle = load_brand_corpus("thin_brand", brands_root=FIXTURES)
    assert "thin brand" in bundle.voice_profile.lower()
    assert "Just a brand-voice file" in bundle.voice_profile
    # is_thin only triggers on kit_default voice now (Plan 10 cleanup).
    # A brand with a real brand-voice.md but no voice-profile.md is not thin.
    assert bundle.is_thin is False
    assert bundle.recent_deliverables == []


def test_empty_brand_uses_kit_defaults():
    bundle = load_brand_corpus("empty_brand", brands_root=FIXTURES)
    assert bundle.is_thin is True
    assert len(bundle.voice_profile) > 0
    assert bundle.recent_deliverables == []


def test_missing_brand_raises():
    with pytest.raises(FileNotFoundError):
        load_brand_corpus("does_not_exist", brands_root=FIXTURES)


def test_sources_dict_records_provenance():
    bundle = load_brand_corpus("rich_brand", brands_root=FIXTURES)
    assert "voice_profile" in bundle.sources
    assert bundle.sources["voice_profile"].endswith("voice-profile.md")
    assert "brand_voice_rules" in bundle.sources


def test_thin_brand_sources_indicate_fallback():
    bundle = load_brand_corpus("thin_brand", brands_root=FIXTURES)
    assert bundle.sources["voice_profile"].endswith("brand-voice.md")


def test_empty_brand_sources_indicate_kit_default():
    bundle = load_brand_corpus("empty_brand", brands_root=FIXTURES)
    assert bundle.sources["voice_profile"] == "kit_default"
    assert bundle.sources["brand_voice_rules"] == "kit_default"


def test_deliverables_sorted_by_mtime_descending(tmp_path):
    brands_root = tmp_path
    brand_dir = brands_root / "mtime_test" / "deliverables" / "recent"
    brand_dir.mkdir(parents=True)
    (brands_root / "mtime_test" / "brand-voice.md").write_text("# voice\n")

    paths = []
    for i in range(1, 8):
        p = brand_dir / f"post-{i}.md"
        p.write_text(f"post {i}")
        os.utime(p, (1700000000 + i * 100, 1700000000 + i * 100))
        paths.append(p)

    bundle = load_brand_corpus("mtime_test", brands_root=str(brands_root))
    assert len(bundle.recent_deliverables) == 5
    names = [name for name, _ in bundle.recent_deliverables]
    assert names[0] == "post-7.md"
    assert names[-1] == "post-3.md"


def test_deliverables_walks_subdirs_when_recent_missing(tmp_path):
    brands_root = tmp_path
    brand_dir = brands_root / "no_recent" / "deliverables" / "social"
    brand_dir.mkdir(parents=True)
    (brands_root / "no_recent" / "brand-voice.md").write_text("# voice\n")
    for i in range(1, 4):
        (brand_dir / f"post-{i}.md").write_text(f"post {i}")

    bundle = load_brand_corpus("no_recent", brands_root=str(brands_root))
    assert len(bundle.recent_deliverables) == 3


def test_voice_profile_preferred_over_brand_voice_when_both_exist():
    bundle = load_brand_corpus("rich_brand", brands_root=FIXTURES)
    assert "lowercase. punchy" in bundle.voice_profile


def test_brands_root_default_used_when_omitted(monkeypatch, tmp_path):
    monkeypatch.setenv("BRANDS_ROOT", str(tmp_path))
    fake_brand = tmp_path / "envtest"
    fake_brand.mkdir()
    (fake_brand / "brand-voice.md").write_text("# env test voice\n")
    bundle = load_brand_corpus("envtest")
    assert "env test voice" in bundle.voice_profile


def test_concept_patterns_directory_present():
    """references/concept-patterns/ must ship six exemplars + README."""
    import os
    here = os.path.dirname(__file__)
    patterns_dir = os.path.abspath(
        os.path.join(here, "..", "references", "concept-patterns")
    )
    assert os.path.isdir(patterns_dir)
    expected = {
        "README.md",
        "stack_contrast.md",
        "agency_anchor.md",
        "dated_personal_anecdote.md",
        "named_framework_close.md",
        "borrowed_authority.md",
        "insider_observation.md",
    }
    actual = set(os.listdir(patterns_dir))
    assert expected.issubset(actual)


def test_load_brand_corpus_rejects_path_traversal():
    import pytest
    with pytest.raises(ValueError, match="brand_slug"):
        load_brand_corpus("../../../etc", brands_root=FIXTURES)


def test_load_brand_corpus_rejects_invalid_slug_chars():
    import pytest
    with pytest.raises(ValueError, match="brand_slug"):
        load_brand_corpus("BAD/CHARS", brands_root=FIXTURES)
