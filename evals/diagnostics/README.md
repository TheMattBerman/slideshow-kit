# Face-Continuity Diagnostics

One-shot scripts for empirically deciding pipeline architecture before refactoring the kit.

## 2026-05-04: face_continuity

Compares three pipelines on a 5-slide script:

- **control**: 5 independent /edits calls with single source ref (current pipeline)
- **batch**: 1 /edits call with n=5 + multi-panel prompt + single source ref
- **anchor**: 5 sequential /edits calls; slide N uses [source_ref, face_crop(slide_{N-1})]

Run:

```bash
export OPENAI_API_KEY=sk-...
python evals/diagnostics/face_continuity_2026_05_04.py \
  --brand matt \
  --script brands/matt/scripts/2026-05-04-photographer-test.md \
  --output-root brands/matt/runs/2026-05-04-diag
```

Cost: ~$1.20 (3 variants x 5 high-quality 1024x1024 images at gpt-image-2 pricing).

Prerequisites:
- `OPENAI_API_KEY` must be set
- `anchor` variant requires ImageMagick (`brew install imagemagick`)

After run, score with `face_score.py` (Task 0.5) and inspect outputs in a contact-sheet view. Decision rubric in `comparison.md` (manual write-up).

## Variant flag

Pass `--variants control,batch,anchor` to run a subset (default: all three). Useful when re-running just one variant without burning the others again.
