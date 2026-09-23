# Code Review: CBRD-27325 / PR #7887

## Review Metadata

| Field | Value |
|---|---|
| Ticket | [CBRD-27325](http://jira.cubrid.org/browse/CBRD-27325) |
| Pull request | [CUBRID/cubrid#7887](https://github.com/CUBRID/cubrid/pull/7887) |
| Title | `[CBRD-27325] Rediscover free heap pages so bulk-deleted space is reused by bestspace` |
| Review date | 2026-09-23 (Asia/Seoul) |
| Pinned PR head | `fee50e3c95d5dfb6b31596d522feafb4b860c387` |
| Live base ref / SHA | `develop` / `bc218a8b878319653cbbdd0fa15fe304b34b1028` |
| Three-dot merge-base | `8ab924bffbfc33dcb7f4a68e9018d0acabe53e5d` |
| Commit list | `fee50e3c9 [CBRD-27325] Rediscover free heap pages so bulk delete space is reused` |
| Changed files | `src/storage/bestspace.cpp` (+170), `src/storage/bestspace.hpp` (+15) |
| Final decision | `COMMENT` (`COMMENTED`) |
| Published review | [review 5288683956](https://github.com/CUBRID/cubrid/pull/7887#pullrequestreview-5288683956) |

The reviewed range was fixed before inspection:

```text
git diff bc218a8b878319653cbbdd0fa15fe304b34b1028...HEAD
git log bc218a8b878319653cbbdd0fa15fe304b34b1028..HEAD --oneline
```

The worktree remained at the pinned head throughout. The pre-existing modified `cubrid-cci` submodule was not initialized, updated, staged, reset, or otherwise touched.

## Sources and Evidence

- Authoritative specification: live `cubrid-jira search CBRD-27325` result, refreshed on 2026-09-23 and cached at `/home/vimkim/.local/share/cubrid-jira/issues/CBRD-27325.md`.
- PR description, the single commit, changed files, and current checks were read from GitHub.
- Repository guidance: `/home/vimkim/my-cubrid/CUBRID.md`, `AGENTS.md`, `src/AGENTS.md`, `src/storage/AGENTS.md`, and `CONTRIBUTING.md`.
- Existing review conversation was audited through all three GitHub endpoints: inline review comments, review summaries, and PR discussion comments. Greptile had already identified the same two functional defects; both were independently verified against the exact head and surrounding queue/state-transition code.
- Relevant surrounding implementation inspected: candidate selection and popping (`bestspace.cpp:797-890`), candidate validation/allocation (`:957-1032`), queue mutation (`:1122-1310`), bestspace lookup (`:1428-1507`), rediscovery (`:1601-1717`), and vacuum candidate publication (`heap_file.c:4651-4696`).

## Validation

- `git diff --check bc218a8b878319653cbbdd0fa15fe304b34b1028...HEAD`: passed with no whitespace errors.
- GitHub code-style, cppcheck, memory-monitor, license, debug build, and release build checks: passed.
- Latest full regression request: SQL `17,459/17,459` passed; medium `975/975` passed; shell had 7 failures among 3,244 executed cases. The seven shell paths are unrelated by name to bestspace/CBRD-27325, but this review does not claim they are proven unrelated.
- Both linked testcase PRs (`cubrid-testcases#3444`, `cubrid-testcases-private-ex#4093`) remain draft and contain zero changed files. The TC merge gate therefore remains failed, and no automated testcase specifically locks down the new state transitions.
- No source was edited and no local build was required: the exact head already has successful debug/release CI builds. The functional findings were validated by tracing deterministic control/data-flow interleavings.

## Standards

No documented-standard violations were found. In particular, the new successful ordered page fix is paired with `pgbuf_ordered_unfix`, and the change adds no exception, allocation/free, include-order, or error-code violations.

The Standards sub-review found three non-blocking Fowler smell heuristics (judgement calls, not hard violations):

1. **Duplicated Code** — `src/storage/bestspace.cpp:1381-1386` and `:1399-1404` duplicate the scan re-arm transition (`m_scan_fruitless = 0`, `m_scan_enabled = true`) in both candidate-push methods. A helper would keep this state transition in one place.
2. **Mysterious Name** — `src/storage/bestspace.cpp:1707-1708` uses `rn` and `rs` only as output sinks for record count and record-size sum. Descriptive names, or a page-count-only query, would make the intent clearer.
3. **Speculative Generality** — `src/storage/bestspace.hpp:388-391` exposes `rediscover` publicly although its sole caller is the nested `shard` implementation at `bestspace.cpp:1093`. It can remain private unless external use is intended.

These judgement calls were not included in the published blocking feedback because tooling enforces the formatting matters and none of the smells independently threatens correctness.

## Spec

The ticket's required result is: “delete 로 비워진 페이지가 다음 insert 에 재사용되어 Num_pages 가 정체한다.” The implementation is incomplete in two independently actionable ways.

### P1 — The rediscovery retry discards the first partial candidate batch

**Evidence:** `src/storage/bestspace.cpp:1082-1101`, especially `:1093-1096`; callee reset at `:854-856`; queue pop removes entries at `:1216-1240`.

1. The first `allocate_get_candidates_or_update_residents()` call can pop one to three nonresident reusable pages and return `NOT_FOUND` with `num_candidates < ALLOC_BATCH_SIZE`.
2. `rediscover()` then publishes at least one additional page.
3. The second call assigns `num_candidates` from a fresh `allocate_pick_candidates()` result and overwrites the same `candidates` array.
4. The first partial batch is neither merged, validated, nor returned to the queue. It is therefore lost from bestspace discovery.
5. If the new scan contributes fewer than four usable pages, `allocate_verify_or_allocate()` allocates the remainder even when the two batches together were sufficient.

This recreates the ticket's central failure mode—free pages become unrecorded and the heap grows unnecessarily. Preserve and merge the first batch, or explicitly requeue it before retrying.

### P1 — Candidate publication can lose the scan re-arm event

**Evidence:** `src/storage/bestspace.cpp:1381-1385`, `:1399-1403`, and `:1697-1713`.

The push paths publish a candidate and only re-arm when their separate load observes `m_scan_enabled == false`. A fruitless scanner independently stores `false`. This legal interleaving loses the wake-up:

```text
push thread                         scanner
-----------                         -------
publish new free-page candidate
load m_scan_enabled == true
skip re-arm                         store m_scan_enabled = false
```

`m_scanning` serializes scanners only; it does not serialize vacuum/delete pushes. Once the bounded candidate queue drains, rediscovery remains disabled despite fresh free space, so subsequent inserts can return to heap extension. The disable/re-arm transition needs serialization or a generation/state protocol that cannot overwrite a newer publication event.

No CBRD-27331 `HEAP_PAGE_VACUUM_UNKNOWN` behavior was added, so no scope creep into that explicitly separate issue was found.

## Final Decision

The review was published as `COMMENTED`, not approved, because the two P1 findings can violate the core CBRD-27325 plateau requirement. No `REQUEST_CHANGES` review was submitted. GitHub recorded review ID `5288683956` against commit `fee50e3c95d5dfb6b31596d522feafb4b860c387` at 2026-09-23T08:37:58Z.

**Axis summary:** Standards — 3 non-blocking judgement-call smells, worst: duplicated scan-state transition; Spec — 2 P1 findings, worst (tie): partial candidate loss and lost scan re-arm.
