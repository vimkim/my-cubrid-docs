> Status updated 2026-10-07: Pinned remote-head review package at aecce0e, reused unchanged from docs commit71bcfef. It explains the former marker/raw-pointer design; local follow-up verification is separate.
> Current entry point: [CBRD-27089](../README.md). Historical evidence below is preserved.

# PR #7927 review package

Pinned Engine HEAD: `aecce0e1216a813771621c13112c8f27d43df22e`.
Pinned exact merge base: `fb567a629cdb390fff920542173fa36f454c74a0`.

Start with the [CI attribution report](../ci_analysis_report_aecce0e_codex.md), then the [code review guide](code_review_guide.md). The guide has an individual What / Why it exists / Why changed here explanation for all changed function and type definitions, including test bodies and inline/deleted methods. It also covers six cleanup lambdas, macros and changed declaration locations.

The package is local documentation and verification evidence. Source and testcase checkouts were read at pinned commits without changing their working trees. No new CI, local regression run or GitHub/JIRA publication was performed. Historical PR-body verification claims are described as historical rather than rerun.

Captured `*-diff.txt` evidence preserves the CI output's SQL column padding. A narrow Git whitespace attribute permits those original trailing spaces; authored prose and scripts retain normal whitespace checks.

## Reproduce documentation checks

Run from this documentation worktree. `uv` provides script dependencies in its cache; use the system Python for tree-sitter.

```bash
uv run --python /usr/bin/python3 --with tree-sitter --with tree-sitter-cpp \
  python cbrd-27089/review-aecce0e/evidence/inventory_symbols.py \
  /home/vimkim/gh/cb/CBRD-27089-oos-deferred-write
python3 cbrd-27089/review-aecce0e/evidence/audit_hunks.py \
  /home/vimkim/gh/cb/CBRD-27089-oos-deferred-write
python3 cbrd-27089/review-aecce0e/evidence/build_guide.py
```

CI acquisition was one `cubrid-ci status`, one `cubrid-ci collect` with the exact HEAD and one `cubrid-ci collect-base`, all suites, no `--wait` or binary download. The commands' saved result files for this invocation are retained at `/home/vimkim/tmp/pr7927-ci-review.uLwiYd`. Revalidate the existing bundles without remote acquisition:

```bash
uv run --with jsonschema python cbrd-27089/review-aecce0e/evidence/validate_ci.py \
  /home/vimkim/tmp/pr7927-ci-review.uLwiYd
python3 /home/vimkim/.agents/skills/cubrid-ci-analyze/scripts/report_mode.py \
  /home/vimkim/tmp/pr7927-ci-review.uLwiYd/assessment.json
```

Expected documentation coverage: 126 inventory records, 109 individual explanations, 87 functions, 9 types, 6 lambdas, 136 classified hunks and zero missing explanations/unclassified hunks. Expected evidence: complete head/base observations, 780 digest-checked raw files per bundle, six head failures, five baseline failures, and `mode=full` with comparison confined to validated cases. Differing CTP revisions still limit medium attribution despite complete collection.

[Final documentation checks](evidence/final-review.json) confirm all 109 three-part explanations, 30 local Markdown links, 132 pinned source anchors, the 19-file net diff and the complete six-case classification. The source worktree's pre-existing changes were preserved.
