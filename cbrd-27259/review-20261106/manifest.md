# Review manifest: CUBRID PR #8416

- Repository: CUBRID/cubrid
- Request: `/cubrid-code-review` of PR #8416 via subagents (2026-11-06)
- Comparison: PR mode. `git diff d52b1889e907abcf84190ec504dde3bc93de260d 9ae07b9491b1393841ecb0f3579752a598bf68ec`
  - base (feature/oos-merge): d52b1889e907abcf84190ec504dde3bc93de260d
  - head (CBRD-27259-storage-force-inline): 9ae07b9491b1393841ecb0f3579752a598bf68ec
  - merge base: d52b1889e907abcf84190ec504dde3bc93de260d
  - patch sha256: e7ffb9028b12bb73c69a075b0adabb01eb57f1a7a0883ff9157e83ea5dce990d (`evidence/pr8416.patch`)
  - 22 modified paths, no renames, deletions, submodules or binaries (`evidence/changed-files.txt`)
- Snapshot time: 2026-11-06
- Source checkout: /home/vimkim/gh/cb/CBRD-27259-storage-force-inline (clean, HEAD = head SHA), build `build_preset_debug_gcc`
- Policy: /home/vimkim/my-cubrid/CUBRID.md, AGENTS.override.md
- Specification: /home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md (sections on STORAGE policies, line ~100-115, and REC_BIGONE)
- PR description: https://github.com/CUBRID/cubrid/pull/8416 ; local copy /home/vimkim/gh/my-cubrid-docs/cbrd-27259/pr-body-rev2.md

## Budget
- Mode: best effort, authorized by the user on 2026-11-06 ("Best effort, 4명").
- Enforcement: none. Claude Code has no cumulative spend cap. Per-agent ceiling (5% weekly / 10% daily) is unverified.
- Usage telemetry: not available per agent. Usage reported as unknown.
- Envelope: 4 reviewer agents, no retries, no nested agents; coordinator reserves replay of candidate findings.
- Per-agent scope target: assigned paths only, at most one focused runtime probe each, stop and report at a natural checkpoint.

## Agents
| Seat | Model | Assignment | Output |
|---|---|---|---|
| systems | opus | C/C++ correctness, error code, notification helper, heap layout guard, catalog/dbi plumbing | reviewers/systems/report.md |
| storage-recovery | sonnet | Heap/OOS layout with FORCE_INLINE, disk representation, recovery/redo and vacuum interaction | reviewers/storage-recovery/report.md |
| schema | opus | Parser, execute_schema ALTER/CREATE semantics, printer, unload | reviewers/schema/report.md |
| ha-concurrency | sonnet | HA replication of DDL and records, concurrency of layout path and notification | reviewers/ha-concurrency/report.md |

Shared challenge Q1 (systems + storage-recovery): can any write path place a FORCE_INLINE value in OOS, or wrongly accept/reject a record (OOS+REC_BIGONE rule, -1388 vs -1393)?

## Verification resources
- Coordinator owns builds. Reviewers must not rebuild or modify the source tree.
- Reviewers may run existing unit-test binaries and csql only with their own `CUBRID_DATABASES` under their reviewer directory.
