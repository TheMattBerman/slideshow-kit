#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(git rev-parse --show-toplevel)"
  TMP="$BATS_TMPDIR/pc-$$"
  mkdir -p "$TMP/run"
  cat > "$TMP/run/concepts.md" <<'EOF'
# Concepts

## Concept 1 (rank: 1, concept_score: 8.7, claims_personal_fact: false)

**Format:** numbered_diagnostic
**Close action:** save

### Hook variants
1. (observation, shock 47) "first hook variant for concept 1."
2. (single_claim, shock 44) "second hook variant for concept 1."

## Concept 2 (rank: 2, concept_score: 8.2, claims_personal_fact: true)

**Format:** narrative
**Close action:** save

### Hook variants
1. (scene, shock 38) "first hook variant for concept 2."

## Concept 3 (rank: 3, concept_score: 7.5, claims_personal_fact: false)

**Format:** receipt_context
**Close action:** comment

### Hook variants
1. (dialogue, shock 35) "first hook variant for concept 3."
EOF
}

teardown() {
  rm -rf "$TMP"
}

@test "pick_concept: --concept 1 writes concept-pick.md" {
  run "$REPO_ROOT/skills/concept-generator/scripts/pick_concept.sh" \
      --run-dir "$TMP/run" --concept 1

  [ "$status" -eq 0 ]
  [ -f "$TMP/run/concept-pick.md" ]
  grep -q "Concept 1" "$TMP/run/concept-pick.md"
  grep -q "numbered_diagnostic" "$TMP/run/concept-pick.md"
}

@test "pick_concept: --concept out-of-range exits non-zero" {
  run "$REPO_ROOT/skills/concept-generator/scripts/pick_concept.sh" \
      --run-dir "$TMP/run" --concept 99

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'out of range'
}

@test "pick_concept: autopilot picks highest non-personal" {
  run "$REPO_ROOT/skills/concept-generator/scripts/pick_concept.sh" \
      --run-dir "$TMP/run" --mode autopilot

  [ "$status" -eq 0 ]
  grep -q "Concept 1" "$TMP/run/concept-pick.md"
}

@test "pick_concept: autopilot fails when all concepts are personal" {
  cat > "$TMP/run/concepts.md" <<'EOF'
## Concept 1 (rank: 1, concept_score: 8.0, claims_personal_fact: true)
**Format:** narrative
**Close action:** save
### Hook variants
1. (scene, shock 30) "personal hook one."
EOF

  run "$REPO_ROOT/skills/concept-generator/scripts/pick_concept.sh" \
      --run-dir "$TMP/run" --mode autopilot

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'no autopilot-safe'
}

@test "pick_concept: missing run-dir exits non-zero" {
  run "$REPO_ROOT/skills/concept-generator/scripts/pick_concept.sh" \
      --run-dir "$TMP/missing" --concept 1

  [ "$status" -ne 0 ]
  echo "$output" | grep -qi 'not found'
}

@test "pick_concept: --concept content matches concepts.md section" {
  run "$REPO_ROOT/skills/concept-generator/scripts/pick_concept.sh" \
      --run-dir "$TMP/run" --concept 2

  [ "$status" -eq 0 ]
  grep -q "Concept 2" "$TMP/run/concept-pick.md"
  grep -q "first hook variant for concept 2" "$TMP/run/concept-pick.md"
}
