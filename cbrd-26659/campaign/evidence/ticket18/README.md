# Ticket 18 evidence checkpoint

This directory preserves the representation campaign's 2026-09-21 evidence against engine
`f4299ac0cd777a2a964c1f197ae5ebf9841a4936`. It is a historical checkpoint, not a claim of campaign
acceptance or current engine acceptance. The pinned specification and implementation differences
in [the oracle](expected-oracle.md) must be read at their recorded revisions.

## Remaining work recorded by this checkpoint

- [Promotion records](promotions.json) flag the gate-boundary and eligibility-floor cases for
  user sign-off. Committing these records does not supply that sign-off.
- The oracle records independent review as outstanding through the promotion notes.
- [The matrix](matrix.json) contains 56 PASS rows, two BLOCKED rows and 12 rows without an
  outcome. These are requirement/configuration rows, not distinct testcase counts.
- Replay indexes retain external bundle locations. On 2026-09-29, the candidate reviewer found
  no `.result` files at the recorded `inv-T18-0003` bundle path; candidate results could not be
  re-reviewed during this repository cleanup. Preserve the indexes and their original hashes.

## Cleanup verification, 2026-09-29

The fixture derivation self-test passed. All 17 generated SQL cases matched the relocated
testcase worktree when supplied explicitly with `--out`; the generator's historical default
under `/home/vimkim/gh/tc/` no longer exists. All 151 campaign records passed the existing
schema and semantic validator. That validation does not establish availability of external
bundles: its bundle-content checks apply only when the recorded root exists.

```bash
python3 cbrd-26659/campaign/evidence/ticket19/derive_ticket19_sizes.py --self-test
python3 cbrd-26659/campaign/evidence/ticket19/gen_ticket19_cases.py --check \
  --out /home/vimkim/gh/cubrid-testcases/cubrid-testcases-cbrd-26659/sql/_36_guava/cbrd_26659/cases
python3 cbrd-26659/campaign/tools/validate_records.py \
  cbrd-26659/campaign/evidence/ticket18 --quiet
```

No engine regression suite was rerun for this cleanup.
