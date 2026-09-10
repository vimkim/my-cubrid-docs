# PR 7600 teaching book

Open [index.html](index.html) for the complete offline book. It embeds its stylesheet and five SVG diagrams and needs no server or network. Individual chapter HTML files provide shorter reading pages. The [combined Markdown](report.md) is a generated convenience copy.

On narrow screens, wide diagrams, code and tables scroll within their own panels to keep text legible. The page itself fits the viewport.

## Edit and rebuild

Edit the numbered Markdown chapters, except generated chapter 6 (diff appendix) and chapter 10 (source map). Edit SVG files in `assets/` directly. Hunk commentary lives in `scripts/hunk_notes.py`; evidence entries live in `scripts/claim_catalog.py`. Rebuild all outputs with:

```bash
cd /home/vimkim/gh/my-cubrid-docs/cbrd-27089/teaching
python3 scripts/build.py
python3 scripts/verify.py
python3 /home/vimkim/.codex/skills/my-code-analysis-report/scripts/reportctl.py verify --report-dir "$PWD"
```

Rendering requires Python 3 and Python-Markdown (`markdown`, version recorded in `evidence/build-inputs.json`). These are already available in the creation environment. Rendering is offline. The evidence extraction additionally requires the recorded source worktree and commits. It refuses a moved HEAD or edits to the six diff files; update provenance deliberately for a new edition. There are no CDN, font or JavaScript dependencies in the reader.

## Reading order

Read foundations, OOS ownership, two-pass flow and side effects before the diff appendix. Then study errors and tests, attempt the review exercises and consult the separate answers. `learning-progress.md` starts unassessed.

## Evidence

Head `b871ea386d2c5419b7abae07dda58b9b7f36377a`; base/merge base `2940b1cfbc3c2d4d0fac3f9244a960350debd380`. Thirty hunks, six files, 306 additions, 23 deletions. `analysis-manifest.json` holds the claim ledger. `evidence/pr-7600.patch` preserves the original diff. The numbered appendix links every hunk to its explanation. `evidence/source-excerpts.json` captures cited source intervals for offline inspection.

`evidence/regression.json` records one fresh passing standalone regression on a private database using the existing binary, including its hash and environment. It is not evidence of a rebuild, old-version reproduction or full-suite run. The test script preserves its owned temporary database for inspection; its exact path is in that file. No shared database/configuration or engine source was changed.

To repeat only that experiment, run `python3 scripts/run-regression.py`, then rebuild the book. Each run creates a fresh private environment and retains it. The script intentionally does not invoke the existing global server-stop cleanup fixture. Broader UPDATE/LOB/vacuum/crash experiments are recorded as open coverage, not implied to have passed.

## Verification

`evidence/validation.json` records static artifact checks. `evidence/browser-validation.json` records browser checks at desktop and mobile widths with network blocked, including screenshot filenames. `evidence/skill-verification.json` records the analysis verifier result. Screenshot images are supplementary review artifacts, not page dependencies.

The book documents two reconciliations: this head's ordinary OOS threshold differs from the normative context, and the current vacuum helper's success-with-null behavior differs from a simplified historical abort narrative. These distinctions are part of the lessons.
