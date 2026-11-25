# Code review: CUBRID/cubrid#8694 and TC PRs (CBRD-27969)

Review of [CUBRID/cubrid#8694](https://github.com/CUBRID/cubrid/pull/8694) "[CBRD-27969] Send the key of the C API unique lookups in the shape of the index they search" (author YeunjunLee), with its testcase PRs [cubrid-testcases-private-ex#5099](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/5099) and [cubrid-testcases#4401](https://github.com/CUBRID/cubrid-testcases/pull/4401). Workflow: `cubrid-code-review`, 2026-11-25 (Asia/Seoul).

**Result.** The fix does what it sets out to do. Without it, a debug server asserts in `btree_compare_key ()` on the TC's lookups. With it, the server answers all of them, and the new TC passes 15/15 on the head build and fails 15/15 on the base build. One low-impact defect remains (F1). In a one-attribute `db_find_multi_unique ()` call on a **prefix index**, the new path sends the full value as the key, so the call silently returns a wrong row or misses the exact value. The base code asserted (debug) or returned an error (release) in the same call. The fix is a two-condition guard.

## Snapshot

| Item | Value |
| --- | --- |
| Engine repository | `CUBRID/cubrid`, PR #8694 into `develop` |
| Base (`develop`) | `e23905d89ad8a49f17e7cff6eaef01a00de258fe` |
| Head | `abf044abcd1b6ea1cdecaa3daaac21ee4660183e` (merge of develop into `23ed0bfd38`) |
| Merge base | `e23905d89ad8a49f17e7cff6eaef01a00de258fe` |
| Comparison | `git diff e23905d89ad8a49f17e7cff6eaef01a00de258fe abf044abcd1b6ea1cdecaa3daaac21ee4660183e` |
| Patch SHA-256 | `93d96bf3e74b3b82437b7fc98a646dde6bf7acb3cbca860f08831d420fd8599f` |
| Changed paths | `src/object/object_accessor.c` (+70/−16), the only path |
| Private TC PR | `cubrid-testcases-private-ex#5099`, head `80163a4b1db495d2a027fbb2fd93e24883791f47`, base `40bb2172826810fc9a11f19621611605a8f44a12`; adds `shell/_06_issues/_26_2h/cbrd_27969/cases/{cbrd_27969.c,cbrd_27969.sh}` |
| Public TC PR | `cubrid-testcases#4401`, draft placeholder created by the bot, 0 changed files |

The PR head and base had not moved when this report was written.

## Verdict

| Item | Value |
| --- | --- |
| Verdict | `changes-required`: one confirmed P3 finding (F1) |
| Coverage | Complete for the changed path and its callers. Release-build runtime was not run (see Limits) |
| Follow-up review required | **Yes, small.** Check the F1 fix, or an explicit agreement to defer it to a follow-up issue. Also confirm the pending `gha-ci` suites (`test_sql`, `test_sql_by_cci`, `test_shell`). Neither item needs a new full review |

## Confirmed findings

### F1 [P3]: a one-attribute `db_find_multi_unique ()` on a prefix index returns a wrong row or misses the exact value

- **Location.** `obj_find_multi_attr_internal ()` at [object_accessor.c:3809](https://github.com/CUBRID/cubrid/blob/abf044abcd1b6ea1cdecaa3daaac21ee4660183e/src/object/object_accessor.c#L3809) (index match) and [3873–3881](https://github.com/CUBRID/cubrid/blob/abf044abcd1b6ea1cdecaa3daaac21ee4660183e/src/object/object_accessor.c#L3873-L3881) (new `size == 1` key). The same selection gap exists in `find_unique_index ()` at [3399](https://github.com/CUBRID/cubrid/blob/abf044abcd1b6ea1cdecaa3daaac21ee4660183e/src/object/object_accessor.c#L3399).
- **Preconditions.** A one-column prefix index such as `create index i_pfx on t_pfx (s(2))`, and a C API caller that looks the column up by value. The DDL is accepted on develop.
- **Violated intent.** The PR's own invariant is that the key is sent "in the shape of the index". Its new comment on `find_unique_index ()` describes the selected index as one "whose key is the attribute's own value". A prefix index stores the value truncated to the prefix length (heap key build, `heap_file.c:16703–16708`), so the full value is not the index's key shape. Both selectors accept the index because they test only `attributes[1] == NULL` and `func_index_info == NULL`.
- **Reproduction** (coordinator replay, debug builds, CS mode, one lookup per client process). Table `t_pfx (id int, s varchar(100))` with prefix index `s(2)` and the row `(1,'abc')`:

| Lookup | Correct result | Head `11.5.0.3069-abf044a` | Base `11.5.0.3067-e23905d` |
| --- | --- | --- | --- |
| `db_find_multi_unique (t_pfx, 1, {"s"}, 'ab')` | not found | **found `abc` (wrong row)** | server assertion (server down) |
| `db_find_multi_unique (t_pfx, 1, {"s"}, 'abc')` | found `abc` | **not found** | server assertion (core) |
| `db_find_unique (t_pfx, "s", 'ab')` | not found | found `abc` (wrong row) | found `abc` (same, pre-existing) |
| `db_find_unique (t_pfx, "s", 'abc')` | found `abc` | `ER_OBJ_OBJECT_NOT_FOUND` | same (pre-existing) |
| `db_find_multi_unique (t_pk, 1, {"id"}, 1)`, control | found `one` | found `one` | server assertion (core) |

  The runtime reviewer (R2) first observed these results, and the coordinator reran them on fresh databases. The probe program is R2's `probe.c`, in the `cbrd_27969.c` pattern. Release builds were not run. The PR description reports a coercion error in release for the base's one-attribute multi lookup.
- **Change attribution.**
  - For `db_find_multi_unique ()`, the PR turns a loud failure (debug assertion or release error) into a silent wrong answer. This part is introduced by the change.
  - For `db_find_unique ()`, the wrong row is pre-existing, and the PR keeps it.
  - Because `find_unique_index ()` now skips multi-column and function entries, a prefix index can also be selected in configurations where an earlier entry of the same type used to be chosen.
- **Impact.** Reach is low: a C API caller (not SQL) has to look up a column whose only usable one-column index is a prefix index. No in-tree caller does this. All engine callers use one-column PK or UNIQUE indexes without a prefix. The consequence is a wrong object returned without an error.
- **Fix direction.** Exclude prefix indexes in both selectors, as `query_graph.c:11419` does:
  ```c
  && (cons->attrs_prefix_length == NULL || cons->attrs_prefix_length[0] == -1)
  ```
  Consider excluding filter indexes too (`cons->filter_predicate == NULL`). A filter index gives a false "not found" for a row outside its predicate. That behavior is identical on base and head (see U2), so excluding it is optional. Add a prefix-index check to the TC (`db_find_unique`, and `db_find_multi_unique` with one attribute, expecting `ER_OBJ_INDEX_NOT_FOUND` or `ER_OBJ_INVALID_ARGUMENTS`). The alternative is to state in the PR that prefix indexes are left out and open a follow-up issue.

## Safety facts outside the diff

| Behavior that changed | Fact that makes it safe | Evidence | Level |
| --- | --- | --- | --- |
| `find_unique ()` picks the first **one-column, non-function** index of each type instead of the first cached entry | A one-column non-function B-tree keys the plain attribute value, never a midxkey. The removed DEDUPLICATE feature leaves no hidden column (`system_parameter.h:492`). (F1 is the prefix exception) | R1 source trace of the index key domain. Every non-prefix one-column probe on head was found, with no assertion | 4 |
| Attribute cache (`att->constraints`) versus class constraints (`class_->constraints`) | Both are built from the same class properties with the same type mapping and rebuilt together. A cached btid always has a class constraint of the same type, inherited ones included | R1 source trace (`class_object.c`). Probe on head: inherited `sub` found by `db_find_unique`, `db_dfind_unique`, multi and multi-for-update | 4 |
| Engine callers (`db_user.name`, serial, `_db_synonym`, `db_trigger`, `_db_stored_procedure`, `_db_stored_procedure_code`, histogram 2-attribute lookups) | Each looked-up attribute has a one-column PK or UNIQUE index, which stays the first match. The histogram lookups use two attributes, which still build a midxkey. No in-tree caller uses the one-attribute multi path. Broker, CAS, CCI and JDBC do not call these functions | R1 source trace. On the head debug build, serial, user (with group), synonym, trigger, `AUTO_INCREMENT`, view and PL/CSQL procedure statements all succeeded with no server assertion | 4 |
| One-attribute multi path passes `values[0]` (const cast) | `btree_find_unique ()` and `btree_find_multi_uniques ()` only read and serialize the key. `unique_key` stays NULL and is cleared once, so nothing is freed twice | R1 source trace | 3 |
| NULL value in the one-attribute multi path | The server answers "not found" before any key comparison, also for `S_UPDATE` | TC check 4-1 OK on head | 4 |
| String keys and collation | `find_unique_key_matches ()` now gates the multi path as it already gated `db_find_unique ()`. Both functions agree for `utf8_bin`, `utf8_en_ci` and `utf8_en_cs` columns | R2 probes D1–D7 on head | 4 |
| Locking and fetch versions | `S_SELECT`, `S_UPDATE`, `LC_FETCH_CATALOG_VERSION` and `LC_FETCH_DIRTY_VERSION` are unchanged | Diff inspection | 2 |

**Not applicable.** No recovery, HA or storage format is affected: the change only selects an index and shapes the key on the client. It writes no log record, page or protocol field. Concurrency: lock modes are unchanged, see above.

## Unverified risks and pre-existing behavior

None of these is attributed to the PR. They are listed so that later work can find them.

- **U1, behavior change (intended).** An attribute whose only index is a function index (for example `lower(s)`) now returns `ER_OBJ_INDEX_NOT_FOUND` from `db_find_unique ()`. Base searched the function index with the raw value and could find a row by accident: `'abc'` found `'ABC'`, while `'ABC'` was not found. Head behaves as TC check 2-2 expects.
- **U2, pre-existing.** A filter index (`index (id) where id > 10`) gives a false "not found" for a row outside the predicate. The result is identical on base and head for `db_find_unique ()`, and `db_find_multi_unique ()` answers "not found" on both. See F1's fix direction.
- **U3, pre-existing.** On a hash-partitioned table, `db_find_unique ()` and all its forms report not found for an existing row. The result is identical on base and head, with no assertion.
- **U4, pre-existing.** On a superclass, `db_find_unique (sup, …)` does not find a row stored in the subclass. The result is identical on base and head.
- **U5, pre-existing, out of scope (as the PR states).** `db_find_primary_key ()` with several columns and `db_dfind_multi_unique ()` send a SEQUENCE key to a multi-column index. `do_get_server_obj_id ()` (`execute_statement.c`) is never called and would look up a two-column PK.

## TC PR review

**`cubrid-testcases-private-ex#5099`.** The TC is well constructed:
- It compiles a C client with `xgcc -lcubridcs` and runs one lookup per process against a running server.
- It covers the three `db_find_unique` forms on every index shape the PR handles, the one- and two-attribute multi forms, NULL, BIGINT, the function index, and server liveness.
- Its setup checks abort with `write_nok`, and cleanup stops the server and deletes the DB.
- Native focused run (`testkit shell`, containment on) at TC head `80163a4b1`:
  - Head debug build: `total=1 success=1 fail=0`, 15/15 OK.
  - Base debug build: 15/15 NOK. The first lookup kills the server, and the remaining checks cannot connect.
- Suggested addition (with F1): a prefix-index table and its expected error.
- Documentation nit: the description's table says "Verdict 1-5" for what are check numbers.

**`cubrid-testcases#4401`.** An empty draft placeholder with no files. Close it rather than merge it, following the testcase lifecycle when the engine PR is merged.

## CI status at the snapshot

| Check | State |
| --- | --- |
| github-checks: `license`, `pr-style`, `code-style`, `cppcheck`, `memory-monitor-check` | success |
| `gha-ci`: `build (debug)`, `build (release)`, `test_medium` | success |
| `gha-ci`: `test_sql`, `test_sql_by_cci`, `test_shell` | **pending**: queued in run [45579653059](https://github.com/CUBRID/cubrid/actions/runs/45579653059), started by the author's `/run all` |
| TC Merge Gate, "Check TC PRs" | failure, expected: "TC changes are not on TC develop yet". This clears only when the TC PR is merged |
| `cubrid-testcases-private-ex#5099` | `MERGEABLE`, no checks reported, no reviews yet |

`cubrid-static-check e23905d89a..abf044abcd` reports 0 new cppcheck, clang-tidy or duplicate-code findings. The cyclomatic complexity of `obj_find_multi_attr_internal ()` rises from 39 to 43.

## Coverage

| Path or invariant | Owner | Evidence | Result |
| --- | --- | --- | --- |
| `find_unique_index ()` and `find_unique ()` selection order | R1 (Opus) | Source trace (key domain, constraint lists, inheritance, types). Runtime: TC 1-1..2-2 and probes A1–A4 and C1 | Correct except prefix (F1) |
| `obj_desc_find_unique ()` and `obj_find_unique ()` signature change | R1 | Both call sites pass `class_` from `sm_get_descriptor_component ()` or `au_fetch_class ()`. TC 1-3 (`db_dfind_unique`) OK | OK |
| `obj_find_multi_attr_internal ()`: function-index skip, one-attribute key, type and collation gate | R1 + R2 (Sonnet) + coordinator | Source trace. TC 3-1..4-3. Probes D1–D7 and P1c/P1d, replayed by the coordinator | F1 |
| Engine catalog callers | R1 + R2 | Catalog index definitions, plus a catalog DDL and DML run on head | OK |
| TC #5099 | R2 + coordinator | Native focused shell run on head and base | Pass on head, fail on base |
| Recovery, HA, storage | coordinator | Not applicable: client-side key and index selection only | N/A |
| Concurrency | R1 | Lock and fetch modes unchanged | OK |

Shared challenge question: one-column key shape. R1 answered it from source, and R2 and the coordinator answered it by execution. No independent second model checked the source argument, so execution served as that check.

### Checks run

| Check | Revision and configuration | Result |
| --- | --- | --- |
| `just configure-build-and-install` (preset `debug_gcc`) | head `abf044abcd`; base `e23905d89a` in a separate detached worktree | exit 0, both |
| Native focused shell run of `cbrd_27969` (`testkit shell`, `TESTKIT_CONTAIN=1`, `testkit-focused.py verify`) | TC `80163a4b1`; head and base debug | head pass 15/15; base fail 15/15 |
| R2 probe set (34 probes: inheritance, partition, filter, collation, prefix, function index, catalog DDL) | head and base debug, CS mode | Head: no assertion or core, one server pid throughout. Base: `btree_compare_key ()` assertion (`btree.c:25075`) on every one-attribute multi lookup |
| Coordinator replay of the F1 probes | head and base debug, fresh databases | Matches the F1 table above |
| `cubrid-static-check` | `e23905d89a..abf044abcd` | 0 new findings |

## Limits

- No release build was run. The release behavior of F1 on base (error, not assertion) is taken from the PR description and source.
- The base TC run did not keep the server stack, because the case deletes its DB. The assertion was reproduced separately in the probe runs.
- The remaining `gha-ci` suites had not finished at the snapshot.
- The unique-filter and unique-function index variants could not be created: develop rejects the DDL. Non-unique variants were used.

## Approval readiness

- **#8694:** not ready for approval as is. It becomes ready once F1 is fixed (the guard above, plus a TC check), or once the reviewers explicitly agree to defer F1 to a follow-up issue, and the pending `gha-ci` suites pass. The core fix is sound, and the TC demonstrates it.
- **#5099:** ready apart from the optional prefix-index check that goes with the F1 fix. Merge it only through the testcase lifecycle, together with the engine merge.
- **#4401:** empty. Close it at merge time.

## Budget

Bounded mode with no user ceiling; no hard cap was enforced. Two reviewer agents ran: R1 (source, Opus, about 8 minutes) and R2 (runtime, Sonnet, about 26 minutes, including base and head builds). Coordinator verification ran on top of that. Per-agent token usage is not attributable while other sessions are active. R2 started one stray subagent by mistake; it ran no commands.
