# 06: Migrate four Applied exercise cards

**What to build:** Convert the four executed same-revision quiz families into English prompt/answer documentation cards with exact evidence links and bounded conclusions, without moving executable infrastructure.

**Blocked by:** 02: Establish the complete Question-bank shell

**Status:** ready-for-agent

- [ ] Create one canonical Applied exercise for each executed quiz family: cold/warm reuse, holder accounting, caller-path cleanup, and dirty/WAL/flush/replacement integration.
- [ ] Each prompt asks the reader to predict, inspect artifacts/source, and produce an evidence card or source-tracing artifact before reading the answer.
- [ ] Each answer links the exact existing `quiz.md`, `answer.md`, SQL, JSON, and accepted `rebind-quiz*` evidence where present.
- [ ] State revision, build, configuration, workload, observation, supported conclusion, unsupported conclusion, and receipt boundary without reproducing raw logs.
- [ ] Treat the 27 planned prompts as plans and the 17 executed questions as their stronger descendants where applicable; planned oracles never become Runtime observations.
- [ ] Account for all `PLAN`, `EXEC`, and remaining `GRILL` items in the migration audit.
- [ ] Do not copy runners, SQL, database lifecycle commands, personal paths, or personal `justfile` workflow into the guide.
- [ ] Every prompt/answer follows the canonical schema and pairs by immutable ID/title.
- [ ] Focused evidence/provenance tests, Copyparty checks, and aggregate validation pass for the Applied route.

