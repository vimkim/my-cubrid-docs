# PR #7927 review-fix design interview

State of the `/grill-with-docs` interview for turning the [two-axis review at d08a169](../review-d08a169-claude/README.md) into fixes. **Q1 settled; Q2–Q10 awaiting answers.** Answer in any form, e.g. "Q2–Q10: all recommended" or per-question overrides.

Facts feeding the questions: `ER_OUT_OF_VIRTUAL_MEMORY` is the established allocation-failure pattern in both touched files; `feat/oos` already ships C++ engine modules (`oos_file.cpp`); the loaddb fact-finder (below) confirmed the pruning trio is separable.

---

## Q1 — Where does the paper trail live? ✅ SETTLED

Glossary terms → `my-cubrid-docs/CONTEXT.md`; ADRs → `my-cubrid-docs/adr/`; this interview + design records → `my-cubrid-docs/cbrd-27089/design/`; implementation tickets → GitHub Issues on `vimkim/cubrid` (set up via `docs/agents/issue-tracker.md`, git-excluded). Nothing enters the CUBRID org repo but code.

## Q2 — What replaces the six `try/catch (std::bad_alloc)` sites?

The standard forbids C++ exceptions in engine code, but `std::vector` growth throws — there is no exception-free `reserve`. Options:
- (a) one **single exception boundary**: a small checked helper in the `heap_prepared_row` module that wraps allocation-throwing calls exactly once, maps `bad_alloc` → `er_set (ER_OUT_OF_VIRTUAL_MEMORY)` + error return; all six call sites become plain error-checked calls;
- (b) strict conformance: replace `std::vector` with `malloc`/`realloc` + explicit sizing;
- (c) leave as-is, citing the existing `heap_file.c:13345` precedent.

➡️ **(a)** — minimal churn, keeps the owner design, converts scattered breaches into one audited boundary. (b) throws away the container safety the design leans on; (c) leaves a reviewer-visible standards breach on an org PR.

## Q3 — RAII stance for `heap_prepared_row`: conform or record a deliberate deviation?

The repo rule says no RAII for memory in engine C code, but the movable/non-copyable owner IS this PR's core mechanism (no-recopy + rollback safety), and `feat/oos` already ships C++ engine modules. Options:
- (a) keep the RAII owner and record an **ADR** (hard to reverse, surprising without context, real trade-off) documenting why and the constraints it obeys (single exception boundary from Q2, never used from pure-C paths);
- (b) rework to malloc + `free_and_init` C style.

➡️ **(a)** — (b) would be reimplementing the mechanism the review just verified clean.

## Q4 — Extract `src/storage/heap_prepared_row.cpp`?

503 lines of C++ class implementation currently sit in one `*INDENT-OFF*` island in `heap_file.c`, and the diff adds 28 `*INDENT-OFF*` pairs across four `.c` files. Extraction moves the class into an astyle-formatted `.cpp` (CMake additions to server/SA targets); `heap_file.c` keeps only glue.

➡️ **Yes** — also permanently removes the class from GNU-indent's blast radius (the 123-char line and mixed-tab findings are symptoms of hand-formatting inside INDENT-OFF).

## Q5 — Runtime behavior when the serializer bounds check trips?

Replacing the debug-only assert at the two unchecked `memcpy`s (`heap_file.c:14310/14327`):
- (a) debug `assert` **plus** release-mode `er_set (ER_GENERIC_ERROR)` + error return (record and chain roll back in the existing scopes);
- (b) reintroduce `S_DOESNT_FIT` grow-and-retry.

➡️ **(a)** — capacity derives from the same serialized lengths, so a trip is a logic bug; grow-and-retry would mask it. (b) only if you expect legitimate size drift between the two passes.

## Q6 — Replica atomic-apply coverage: in-repo test or external citation?

The `ER_GENERIC_ERROR` guard at `locator_sr.c:7178` (copy area splitting an OOS group) has no test since the runner removal. Options:
- (a) in-repo GoogleTest `TEST_F` exercising `xlocator_repl_force` — guard path + happy path — with fallback to (b) if the unit harness can't reach it;
- (b) cite the covering cubrid-testcases location in the PR body only.

➡️ **(a)** with explicit feasibility check as the ticket's first step — in-repo runs on every CI push; a citation goes stale silently.

## Q7 — Which judgement-call smells get fixed (multi-select)?

1. rename `recdes` → `prepared_rows` (`locator_multi_insert_force` param, `m_recdes_collected`);
2. named reset / scope guard for the 8-site hand-repeated `heap_oos_begin_insert_publication` reset;
3. dedup the retained-bytes expression + name the `8 * 1024 * 1024` constant;
4. remove or gate the 14 `std::printf` sites in tests;
5. consolidate the triplicated `class heap_prepared_row;` forward declaration;
6. refactor 18-param `locator_insert_force`.

➡️ **1–5** (cheap, each closes a named finding); **skip 6** — highest churn, pre-existing pattern, weakest payoff on a PR that needs to converge.

## Q8 — Fix delivery: new commits or history rewrite?

- (a) New `[CBRD-27089]` commits per ticket on `feat/oos-deferred-write`, PR body amended once at the end, then one `/run all` CI re-trigger;
- (b) rebase folding fixes into the existing commits.

➡️ **(a)** — the PR is a draft under review with pinned review links; rewriting invalidates the pinned SHAs and your own evidence chain.

## Q9 — Loaddb trio: split into its own PR or keep-and-disclose?

Fact-finder evidence: pre-PR, CS-mode `cubrid loaddb` into a partitioned table put rows into the ROOT heap (`pruning_type = 0` means "destination already final"; SA mode pruned correctly) — a genuine pre-existing misplacement bug. The trio (pruning derivation + per-partition `BU_LOCK` + `SINGLE_ROW_INSERT`) is NOT needed for this PR's OOS ownership invariant (with `pruning_type = 0`, chain and record both land in root — self-consistent, wrong table). The three changes are inseparable from each other but separable as a whole.

- (a) **Split**: revert the trio here (loader keeps `pruning_type = 0`), file the CS-loader misplacement bug as its own JIRA ticket + PR carrying the trio and the loader partition-routing tests; this PR's "SQL 의미는 바꾸지 않습니다" claim becomes true as written;
- (b) **Keep + disclose**: leave the trio in, amend the PR body with an AS-IS/TO-BE for the misplacement fix.

➡️ **(a)** — a user-visible data-placement change in a shipped utility deserves its own ticket, QA visibility, and review story instead of riding an OOS refactor PR.

## Q10 — The unconditional `SINGLE_ROW_INSERT` inconsistency — which fix?

New finding (not in the published review): `SINGLE_ROW_INSERT` is now passed unconditionally — including the non-partitioned `insert_errors_filtered || !HA_DISABLED()` path that previously used `MULTI_ROW_INSERT` — while the scancache is still started with `MULTI_ROW_INSERT`, leaving `m_index_stats` allocated and unused.

- (a) `SINGLE_ROW_INSERT` only for partitioned classes, restore `MULTI_ROW_INSERT` for the non-partitioned path (scancache kept consistent);
- (b) commit to `SINGLE_ROW_INSERT` everywhere and stop starting the scancache with `MULTI_ROW_INSERT`.

➡️ **(a)** — restores pre-PR behavior for non-partitioned loads (keeps batched unique-stats accumulation, a loaddb performance property) and scopes the semantic change to exactly where it's needed. Lands in whichever PR Q9 chooses.
