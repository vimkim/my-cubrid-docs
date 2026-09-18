# PR #7927 review at d08a169

Reviewed 2026-09-18: [PR #7927](https://github.com/CUBRID/cubrid/pull/7927), `38093ea859a8a08e20405b72b0cb395205bedb2f...d08a169ef5da45dcc4a4fe71c5a131aaf3e6057e` (base `feat/oos`, three-dot merge-base; 15 commits, 14 files, +2653/−249). Two-axis review — Standards and Spec — run as parallel sub-agents over the same pinned diff; the local worktree HEAD equals the PR head. Review only: no source changes were committed or pushed.

**The core deferred-write contract verifies clean against code; no critical findings.** The finalizer writes chains into the destination heap's OOS file after pruning, the 24-byte stub identity stamp is propagated, the no-recopy claim holds, duplicate-key probes write no chains, partition move does not double-finalize, and demotion policy is untouched. The Spec verdict is REVISE: three major findings are undisclosed scope or robustness gaps, not contract violations.

## Standards

5 hard documented-standard breaches and 7 nonblocking judgement calls. The largest breach: six new C++ exception sites (`try` / `catch (std::bad_alloc)`) in engine code against the documented `er_set` + return-code error model. Also a 123-character line and mixed tab/space continuations inside `*INDENT-OFF*` regions that CI formatting cannot repair, RAII-owned buffers instantiated in `.c` files, and two include-order slips. [Standards report](standards.md).

## Spec

3 major and 3 minor findings. Most consequential: an undisclosed loaddb data-placement change (derived pruning type, `BU_LOCK` on every partition, `MULTI_ROW_INSERT` → `SINGLE_ROW_INSERT`) that the PR body's "no SQL semantics changes" claim does not cover. Also: the replica atomic-apply guard has no in-repo test after the Python runner removal, and the prepared-row serializer replaced a bounds-checked writer with unchecked `memcpy`s guarded only by a debug assert. The +1442 test lines are on-topic destination-ownership coverage, not scope creep. [Spec report](spec.md).

---

Standards: 5 hard + 7 optional; worst is C++ exceptions in engine code. Spec: 3 major + 3 minor; worst is the undisclosed loaddb placement/locking/op-type change.
