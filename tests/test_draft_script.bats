#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  TMP="$BATS_TMPDIR/ds-$$"
  mkdir -p "$TMP/run"
  cat > "$TMP/run/concept-pick.md" <<'EOF'
# Picked concept (mode: interactive)

## Concept 1 (rank: 1, concept_score: 8.7, claims_personal_fact: false)

**Format:** numbered_diagnostic
**Close action:** save

### Hook variants
1. (observation, shock 47) "the 4 tells of every AI carousel."
EOF
  cat > "$TMP/run/concept-context.json" <<'EOF'
{
  "brand": "ds-test",
  "mode": "interactive",
  "voice_profile": "lowercase punchy.",
  "brand_voice_rules": "## Avoid\n- synergy\n",
  "is_thin_corpus": false
}
EOF
}

teardown() {
  rm -rf "$TMP"
}

@test "draft_script: --dry-run writes script.md placeholder + concept-meta.json" {
  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
      --run-dir "$TMP/run" --dry-run

  [ "$status" -eq 0 ]
  [ -f "$TMP/run/script.md" ]
  [ -f "$TMP/run/concept-meta.json" ]
  grep -q "format: numbered_diagnostic" "$TMP/run/script.md"
  grep -q "close_action: save" "$TMP/run/script.md"
  grep -q '"format": "numbered_diagnostic"' "$TMP/run/concept-meta.json"
  grep -q '"_schema_version": 2' "$TMP/run/concept-meta.json"
}

@test "draft_script: missing run-dir exits non-zero" {
  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
      --run-dir "$TMP/missing" --dry-run

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'not found'
}

@test "draft_script: missing concept-pick.md exits non-zero" {
  rm "$TMP/run/concept-pick.md"
  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
      --run-dir "$TMP/run" --dry-run

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'concept-pick.md not found'
}

@test "draft_script: --no-lint logs lint_skipped" {
  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
      --run-dir "$TMP/run" --no-lint --dry-run

  [ "$status" -eq 0 ]
  grep -q '"lint_skipped": true' "$TMP/run/concept-meta.json"
}

@test "draft_script: --no-format-check logs format_check_skipped" {
  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
      --run-dir "$TMP/run" --no-format-check --dry-run

  [ "$status" -eq 0 ]
  grep -q '"format_check_skipped": true' "$TMP/run/concept-meta.json"
}

@test "draft_script: writes scene-direction.md alongside script.md (dry-run)" {
  TMP="$BATS_TMPDIR/ds-scene-$$"
  mkdir -p "$TMP/run"
  cat > "$TMP/run/concept-pick.md" <<'EOF'
# Picked concept (mode: interactive)

## Concept 1 (rank: 1, concept_score: 8.7, claims_personal_fact: false)

**Format:** narrative
**Close action:** save
**Arc:** the four tells.
**Visual hook:** matt at desk, late evening lamp warmth, mid-thought.
**Why this works:** placeholder.

### Hook variants
1. (observation, shock 47) "scroll your feed."
EOF

  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
    --run-dir "$TMP/run" --dry-run

  [ "$status" -eq 0 ]
  [ -f "$TMP/run/script.md" ]
  [ -f "$TMP/run/scene-direction.md" ]
  grep -q "source: stage_3" "$TMP/run/scene-direction.md"

  rm -rf "$TMP"
}

@test "draft_script: --no-save-filter records save_filter_skipped in meta" {
  TMP="$BATS_TMPDIR/ds-nsf-$$"
  mkdir -p "$TMP/run"
  cat > "$TMP/run/concept-pick.md" <<'EOF'
# Picked concept
## Concept 1 (rank: 1, concept_score: 8.0, claims_personal_fact: false)
**Format:** narrative
**Close action:** save
**Arc:** test.
**Visual hook:** desk shot.
### Hook variants
1. (observation, shock 30) "h."
EOF

  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
    --run-dir "$TMP/run" --no-save-filter --dry-run

  [ "$status" -eq 0 ]
  grep -q '"save_filter_skipped": true' "$TMP/run/concept-meta.json"

  rm -rf "$TMP"
}

@test "draft_script: concept-meta.json records scene_direction_source=stage_3 and visual_hook" {
  TMP="$BATS_TMPDIR/ds-meta-$$"
  mkdir -p "$TMP/run"
  cat > "$TMP/run/concept-pick.md" <<'EOF'
# Picked concept

## Concept 1 (rank: 1, concept_score: 8.0, claims_personal_fact: false)
**Format:** narrative
**Close action:** save
**Arc:** test.
**Visual hook:** desk shot.
### Hook variants
1. (observation, shock 30) "h."
EOF

  run "$REPO_ROOT/skills/concept-generator/scripts/draft_script.sh" \
    --run-dir "$TMP/run" --dry-run

  [ "$status" -eq 0 ]
  [ -f "$TMP/run/concept-meta.json" ]
  grep -q '"scene_direction_source": "stage_3"' "$TMP/run/concept-meta.json"
  grep -q '"visual_hook": "desk shot."' "$TMP/run/concept-meta.json"

  rm -rf "$TMP"
}
