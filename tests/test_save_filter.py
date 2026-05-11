"""Tests for lib/save_filter.py."""

from lib.save_filter import check_save_worthiness


def test_specific_number_passes():
    body = "spent $40k on agency invoices in march."
    assert check_save_worthiness("REVEAL", body) == []


def test_percent_number_passes():
    body = "ctr jumped from 1.1% to 4.3% on the same spend."
    assert check_save_worthiness("REVEAL", body) == []


def test_iso_date_passes():
    body = "on 2026-03-14 we shipped the new pipeline and tracked the delta."
    assert check_save_worthiness("REVEAL", body) == []


def test_named_month_passes():
    body = "in november we ran the same workflow with nano banana."
    assert check_save_worthiness("REVEAL", body) == []


def test_tactical_aside_passes():
    body = "tip: reverse the order of slides 4 and 5 if your hook leans visual."
    assert check_save_worthiness("REVEAL", body) == []


def test_quote_character_passes():
    body = 'he told me on the call: "the agency model is dead". one line.'
    assert check_save_worthiness("REVEAL", body) == []


def test_named_framework_passes():
    body = "i call this the 4-tells audit. run it before any launch."
    assert check_save_worthiness("REVEAL", body) == []


def test_thin_body_fails_heuristic():
    body = "this is generally important but no specifics."
    violations = check_save_worthiness("REVEAL", body)
    assert len(violations) == 1
    assert violations[0].rule_id == "save_filter_thin_slide"


def test_hook_slot_exempt():
    body = "this is generally important but no specifics."
    assert check_save_worthiness("HOOK", body) == []


def test_cta_slot_exempt():
    body = "save this for later when you need it."
    assert check_save_worthiness("CTA", body) == []


def test_llm_fallback_called_when_heuristic_fails():
    body = "this is generally important but no specifics."
    calls: list[str] = []

    def judge(text: str) -> bool:
        calls.append(text)
        return True

    violations = check_save_worthiness("REVEAL", body, llm_judge_callback=judge)
    assert calls == [body]
    assert violations == []


def test_llm_fallback_can_confirm_failure():
    body = "this is generally important but no specifics."
    def judge(text: str) -> bool:
        return False

    violations = check_save_worthiness("REVEAL", body, llm_judge_callback=judge)
    assert len(violations) == 1


def test_llm_fallback_skipped_when_no_callback():
    body = "this is generally important but no specifics."
    violations = check_save_worthiness("REVEAL", body, llm_judge_callback=None)
    assert len(violations) == 1


def test_llm_fallback_disabled_via_flag():
    body = "this is generally important but no specifics."
    def judge(text: str) -> bool:
        return True
    violations = check_save_worthiness(
        "REVEAL", body, use_llm_fallback=False, llm_judge_callback=judge
    )
    assert len(violations) == 1


def test_violation_message_helpful():
    body = "thin generic line."
    violations = check_save_worthiness("REVEAL", body)
    msg = violations[0].message
    assert "specific" in msg.lower() or "save" in msg.lower()


def test_bare_digit_without_unit_does_not_pass_heuristic():
    """Tightened _RE_NUMBER requires k/m/x/% suffix; bare 'step 1' is filler."""
    body = "in step 1 we open section 2 of the deck."
    violations = check_save_worthiness("REVEAL", body)
    assert len(violations) == 1
    assert violations[0].rule_id == "save_filter_thin_slide"


def test_save_filter_tight_slot_one_marker_passes():
    """<=12-word slots: one marker is sufficient."""
    violations = check_save_worthiness(
        slide_role="ITEM",
        slide_body="i replaced my $11k photographer in 8 minutes.",
        effective_word_cap_max=12,
    )
    assert violations == []


def test_save_filter_tight_slot_zero_markers_fails():
    violations = check_save_worthiness(
        slide_role="ITEM",
        slide_body="this is a short generic statement that means nothing.",
        effective_word_cap_max=12,
    )
    assert any(v.rule_id == "save_filter_thin_slide" for v in violations)


def test_save_filter_standard_slot_one_marker_fails():
    """>=13-word slots: need markers from >=2 categories."""
    violations = check_save_worthiness(
        slide_role="ITEM",
        slide_body=(
            "this body has a single number 7 in it but no dates "
            "frameworks quotes or tactical asides at all."
        ),
        effective_word_cap_max=50,
    )
    assert any(v.rule_id == "save_filter_thin_slide" for v in violations)


def test_save_filter_standard_slot_two_categories_passes():
    violations = check_save_worthiness(
        slide_role="ITEM",
        slide_body=(
            'tuesday 2pm. the FOUR-TELLS test caught it: "we doubled output." '
            "tip: replicate that test on every carousel."
        ),
        effective_word_cap_max=50,
    )
    assert violations == []


def test_save_filter_default_word_cap_max_keeps_one_marker_baseline():
    """Backward-compat: default treats as tight slot (1 marker passes).
    Body with zero markers still fails."""
    violations = check_save_worthiness(
        slide_role="ITEM",
        slide_body="generic statement with no markers at all.",
    )
    assert any(v.rule_id == "save_filter_thin_slide" for v in violations)


def test_llm_callback_auth_error_falls_through_with_warning(capsys):
    """Network/auth errors in the LLM judge fall through to heuristic verdict
    with a stderr warning, not silent swallowing."""
    from urllib.error import HTTPError
    from lib.save_filter import check_save_worthiness

    def auth_failing_judge(text):
        raise HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    body = "this is generally important but no specifics."
    violations = check_save_worthiness(
        slide_role="ITEM",
        slide_body=body,
        effective_word_cap_max=50,
        llm_judge_callback=auth_failing_judge,
    )
    captured = capsys.readouterr()
    assert "save_filter" in captured.err.lower()
    assert "401" in captured.err or "Unauthorized" in captured.err
    assert any(v.rule_id == "save_filter_thin_slide" for v in violations)


def test_llm_callback_runtime_bug_does_not_swallow(capsys):
    """A buggy judge implementation surfaces in stderr."""
    from lib.save_filter import check_save_worthiness

    def buggy_judge(text):
        raise TypeError("judge expected dict, got str")

    body = "this is generally important but no specifics."
    violations = check_save_worthiness(
        slide_role="ITEM",
        slide_body=body,
        effective_word_cap_max=50,
        llm_judge_callback=buggy_judge,
    )
    captured = capsys.readouterr()
    assert "TypeError" in captured.err
    assert any(v.rule_id == "save_filter_thin_slide" for v in violations)
