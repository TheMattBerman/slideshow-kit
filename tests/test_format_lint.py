"""Tests for lib/format_lint.py."""

import json
import os

import pytest

from lib.format_lint import lint_script_structure, CLOSE_VOCAB


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "formats")


def _read(name: str) -> str:
    with open(os.path.join(FIXTURES, name)) as f:
        return f.read()


def test_script_draft_prompt_enforces_single_action_cta_guidance():
    prompts_path = os.path.join(
        os.path.dirname(__file__), "..", "skills", "concept-generator", "prompts.json"
    )
    with open(prompts_path) as f:
        prompts = json.load(f)
    prompt = prompts["script_draft"]["agent_prompt_template"].lower()
    assert "exactly one primary action verb" in prompt
    assert "matching close_action" in prompt
    assert "never combine save/share/comment" in prompt
    assert "save:" in prompt
    assert "share:" in prompt
    assert "comment:" in prompt
    assert "soft:" in prompt


# --- Happy paths: each format's *_ok.md should produce zero violations ---

@pytest.mark.parametrize("fixture,format_name,close_action", [
    ("narrative_ok.md", "narrative", "save"),
    ("numbered_diagnostic_ok.md", "numbered_diagnostic", "save"),
    ("receipt_context_ok.md", "receipt_context", "comment"),
    ("process_reveal_ok.md", "process_reveal", "save"),
    ("anatomy_breakdown_ok.md", "anatomy_breakdown", "save"),
    ("before_after_ok.md", "before_after", "save"),
    ("counter_narrative_ok.md", "counter_narrative", "comment"),
])
def test_happy_path_each_format(fixture, format_name, close_action):
    violations = lint_script_structure(_read(fixture), format_name, close_action)
    assert violations == [], f"{fixture}: {violations}"


# --- Negative paths: each rule_id triggered by a crafted input ---

def test_format_unknown_format_emitted():
    violations = lint_script_structure("# HOOK\nfoo\n", "no_such_fmt", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_unknown_format" in rule_ids


def test_format_missing_slot_emitted():
    # narrative requires HOOK + REVEAL + SETUP + EXAMPLES + OUTCOME + CTA. Skip CTA.
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
    )
    violations = lint_script_structure(text, "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_missing_slot" in rule_ids


def test_format_too_many_slots_emitted():
    # numbered_diagnostic ITEM cap is 8.
    items = "\n".join(
        f"# ITEM {i}\nfifteen words exactly here for the body slide minimum count and not more here."
        for i in range(1, 10)  # 9 items
    )
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n" + items + "\n"
        "# FIX\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nsave this for later when you need to come back to it for sure for sure.\n"
    )
    violations = lint_script_structure(text, "numbered_diagnostic", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_too_many_slots" in rule_ids


def test_format_unknown_role_emitted():
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# UNICORN\nfifteen words exactly here for the body slide minimum count and not more here.\n"
    )
    violations = lint_script_structure(text, "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_unknown_role" in rule_ids


def test_format_word_count_low_emitted():
    text = (
        "# HOOK\nshort.\n"  # 1 word, below hook min 6
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nsave this for later when you need to come back to it for sure for sure.\n"
    )
    violations = lint_script_structure(text, "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_word_count_low" in rule_ids


def test_format_word_count_high_emitted():
    long_body = " ".join(["word"] * 100)  # 100 words, above hook max 15
    text = (
        f"# HOOK\n{long_body}\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nsave this for later when you need to come back to it for sure for sure.\n"
    )
    violations = lint_script_structure(text, "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_word_count_high" in rule_ids


def test_format_close_missing_action_emitted():
    violations = lint_script_structure(_read("bad_close.md"), "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_missing_action" in rule_ids


def test_soft_close_no_vocab_required():
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\njust an observational close with absolutely no action language whatsoever here.\n"
    )
    violations = lint_script_structure(text, "narrative", "soft")
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_missing_action" not in rule_ids


def test_share_close_vocab_match():
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nshare this with the operator who needs to read it most before tomorrow morning.\n"
    )
    violations = lint_script_structure(text, "narrative", "share")
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_missing_action" not in rule_ids


def test_close_multiple_actions_flags_save_share_stuffing():
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nsave this and share it with the operator who needs the reminder tomorrow morning.\n"
    )
    violations = lint_script_structure(text, "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_multiple_actions" in rule_ids
    assert "format_close_missing_action" not in rule_ids


def test_close_multiple_actions_flags_share_comment_stuffing():
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nshare this with your team and comment with the part they should fix first.\n"
    )
    violations = lint_script_structure(text, "narrative", "share")
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_multiple_actions" in rule_ids
    assert "format_close_missing_action" not in rule_ids


def test_close_multiple_actions_flags_save_comment_stuffing():
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nsave this audit and comment with the first section you would rewrite today.\n"
    )
    violations = lint_script_structure(text, "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_multiple_actions" in rule_ids
    assert "format_close_missing_action" not in rule_ids


def test_brand_close_vocabulary_extends_kit_default():
    import tempfile
    bv = (
        "# voice\n\n"
        "## Close vocabulary\n\n"
        "### save\n"
        "- \"screenshot for later\"\n"
        "- \"tap save\"\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(bv)
        bv_path = f.name
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\ntap save now and come back when your next post is ready to ship out.\n"
    )
    # 'tap save' is a brand addition; should satisfy the save vocab check.
    violations = lint_script_structure(text, "narrative", "save", brand_voice_path=bv_path)
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_missing_action" not in rule_ids


def test_brand_close_vocabulary_participates_in_multiple_action_check():
    import tempfile
    bv = (
        "# voice\n\n"
        "## Close vocabulary\n\n"
        "### share\n"
        "- \"pass this to\"\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(bv)
        bv_path = f.name
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nsave this checklist and pass this to the teammate writing tomorrow's draft.\n"
    )
    violations = lint_script_structure(
        text, "narrative", "save", brand_voice_path=bv_path
    )
    rule_ids = [v.rule_id for v in violations]
    assert "format_close_multiple_actions" in rule_ids


def test_close_vocab_check_skipped_when_cta_missing():
    """If CTA is omitted, format_close_missing_action must NOT fire on a non-CTA slide."""
    text = (
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        # No CTA heading on purpose.
    )
    violations = lint_script_structure(text, "narrative", "save")
    rule_ids = [v.rule_id for v in violations]
    # CTA is missing -> format_missing_slot must be present.
    assert "format_missing_slot" in rule_ids
    # The vocab check must NOT misfire on a non-CTA slide.
    assert "format_close_missing_action" not in rule_ids


def test_format_unknown_close_action_emitted():
    """Invalid close_action emits format_unknown_close_action, not format_unknown_format."""
    violations = lint_script_structure(
        "# HOOK\nfoo bar baz qux quux corge grault.\n"
        "# REVEAL\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# SETUP\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# EXAMPLES\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# OUTCOME\nfifteen words exactly here for the body slide minimum count and not more here.\n"
        "# CTA\nsave this for later when you need to come back to it for sure for sure.\n",
        "narrative",
        "bogus",
    )
    rule_ids = [v.rule_id for v in violations]
    assert "format_unknown_close_action" in rule_ids
    assert "format_unknown_format" not in rule_ids


# --- Per-style word_count_override (Plan 9 Task 6.5.4) ---
#
# Note: lib.format_lint.Violation has no `role` field; role is encoded in
# `snippet` as "<ROLE>: <N> words". The over-cap rule_id is
# `format_word_count_high` (not the spec's `format_word_count_out_of_range`).
# Tests below filter by snippet prefix to recover the role.

def test_lint_with_style_override_uses_tighter_range(tmp_path):
    """ITEM body of 14 words violates the override [6, 12] cap even though
    it would NOT violate the format default [15, 50] cap (it would be flagged
    as too LOW under the default; with the override it is flagged as too HIGH)."""
    style_dir = tmp_path / "social_native"
    style_dir.mkdir()
    (style_dir / "style.yaml").write_text(
        "word_count_override:\n  ITEM: [6, 12]\n"
    )
    script = (
        "# HOOK\n"
        "the four tells of a broken funnel here.\n"
        "# ITEM\n"
        "this body is fourteen words long which exceeds the tighter cap by two words now.\n"
        "# ITEM\n"
        "another fourteen word body that should also fail under the override cap of twelve.\n"
        "# FIX\n"
        "the structural fix is one heading swap to numbered diagnostic and explicit cta vocabulary always.\n"
        "# CTA\n"
        "save this audit for later when you come back to ship next post.\n"
    )
    violations = lint_script_structure(
        script, "numbered_diagnostic", "save", style_dir=str(style_dir)
    )
    item_high = [
        v for v in violations
        if v.rule_id == "format_word_count_high" and v.snippet.startswith("ITEM:")
    ]
    assert item_high, [(v.rule_id, v.snippet, v.message) for v in violations]


def test_lint_without_style_override_uses_format_default():
    script = (
        "# HOOK\nthe four tells of a broken funnel here.\n"
        "# ITEM\nthis body has exactly fifteen words to satisfy the format default range minimum reliably ok.\n"
        "# ITEM\nthis body has exactly fifteen words to satisfy the format default range minimum reliably ok.\n"
        "# FIX\nthe structural fix is one heading swap to numbered diagnostic and explicit cta vocabulary always.\n"
        "# CTA\nsave this audit for later when you come back to ship next post.\n"
    )
    violations = lint_script_structure(
        script, "numbered_diagnostic", "save", style_dir=None
    )
    rule_ids = [v.rule_id for v in violations]
    assert "format_word_count_high" not in rule_ids
    assert "format_word_count_low" not in rule_ids


def test_lint_error_message_references_style_yaml_path(tmp_path):
    style_dir = tmp_path / "social_native"
    style_dir.mkdir()
    (style_dir / "style.yaml").write_text(
        "word_count_override:\n  ITEM: [6, 12]\n"
    )
    script = (
        "# HOOK\nthe four tells of a broken funnel here.\n"
        "# ITEM\nthis is a fifteen word body that exceeds the override cap of twelve words easily.\n"
        "# ITEM\nanother fifteen word body that exceeds the override cap of twelve words easily here.\n"
        "# FIX\nthe structural fix is one heading swap to numbered diagnostic and explicit cta vocabulary always.\n"
        "# CTA\nsave this audit for later when you come back to ship next post.\n"
    )
    violations = lint_script_structure(
        script, "numbered_diagnostic", "save", style_dir=str(style_dir)
    )
    item_msgs = [v.message for v in violations if v.snippet.startswith("ITEM:")]
    assert any("style.yaml" in m for m in item_msgs), item_msgs
