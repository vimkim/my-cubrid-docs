---
name: verify-sp-dml-guard
description: Check the proposed SP DML guard model when changing its ancestry rules, access snapshots, or execution lifetime. Use when reviewing a later implementation against this proposal.
---

# Verify the proposed SP DML guard

Read `code-analysis/sp-dml-guard/report.md` and `code-analysis/sp-dml-guard/README.md` from the my-cubrid-docs repository root. This is a proposal model. The engine does not implement the modeled guard at the synchronization commit.

Run `python3 code-analysis/sp-dml-guard/check.py` from the my-cubrid-docs repository root. Completion requires nine `PASS` results. The complete case must have no invariant violation. Each broken variant must violate its specified invariant. Treat a timeout, parser error, missing tool, or unexpected invariant as a failed check.

Read TLA+ results with `/statechart`. Read a counterexample as a path through preparation, active SQL execution, callback execution and return. Report which proposal assumption failed. Claim an engine bug only after matching its transitions to the actual code and reproducing it there. Keep model defects separate from engine findings.

## Source synchronization record

Source repository: `CUBRID/CUBRID`. Source commit: `e64a04a79a5842827a124b3f8313516d0da2594c`.

The record covers source inspection, not implementation equivalence. Source paths below are relative to a CUBRID source checkout, not the my-cubrid-docs root.

- `src/query/execute_statement.c`: `do_execute_statement`, `do_prepare_update`, `do_prepare_delete`, `do_prepare_select`, trigger wrappers, client DML and internal SELECTs.
- `src/parser/xasl_generation.c`: `pt_to_merge_xasl`, class-list generation, DML targets and referenced objects.
- `src/query/xasl.h`: `XASL_NODE`, `XASL_NODE_HEADER`, plan types and DML target structures.
- `src/communication/network_interface_sr.cpp`: `sqmgr_prepare_query` cache-hit replies.
- `src/method/method_callback.cpp`: `callback_handler::prepare`, `execute`, handler reuse and retry.
- `src/method/method_query_handler.cpp`: `query_handler::prepare`, `execute`, `prepare_retry`.
- `src/sp/pl_executor.cpp`: `executor::callback_prepare`, `callback_execute`, `callback_fetch`.
- `src/compat/db_vdb.c`: DB statement execution, compile and replan boundaries.
- `src/object/trigger_manager.c` and `src/parser/compile.c`: trigger activity and statement execution.

Before moving this commit forward, inspect changes to these paths, confirm the abstraction still matches the proposal and rerun the checks. An implemented guard also needs runtime evidence for cache hits, client DML, trigger callbacks, retries and error cleanup. The existing model cannot supply that evidence.

If a proposal rule changes, update its invariant and representative statements, retain a broken variant that demonstrates the check can fail, and rerun. If engine code changes without rechecking this record, use `/maintain-formal-verification-skill` before claiming synchronization.
