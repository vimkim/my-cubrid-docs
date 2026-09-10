# Teaching notes

## Learner preferences and starting point

- Wants thorough line-by-line understanding, but currently needs the meaning of pruning and heap/OVF/OOS ownership explained.
- Asks whether a shared OOS file could replace per-partition files and whether inline probe/rebuild is unnecessarily expensive.
- Do not interpret these questions as established misconceptions or demonstrated mastery.
- Learner requested faster pacing after basic routing checks became too easy. Teach coherent source/design sections and ask occasional design-consequence questions, not repeated elementary routing questions.

## Current checkpoint

- 2026-09-09: learner requested the committed effective-key change `b871ea386...213ce80f5`, at brisk pace. Lesson 0005 pairs one INSERT with one moving UPDATE; HTML/SVG and Markdown are available as teaching material, not a settled learning record. Await explanation of why moving UPDATE retains source p0 while choosing destination p1 and why final disagreement rejects. Then trace defaults, supplied-old values and dedicated increments. No new mastery inferred from implementation/review approval.

- Lesson 0001: learner correctly selected p1 for id = 10 and excluded p0. Used read/search terminology for an insert; teacher clarified destination selection. Do not claim this distinction has been independently demonstrated yet.
- Published the first HTML lesson and SVG after the correct boundary prediction.
- Lesson 0002: learner correctly selected H0 for id = 7, explaining id < 10 → p0 → H0. Published HTML using the existing partition-heaps SVG.
- Lesson 0003: learner correctly selected OOS1; numeric wording was corrected (12 satisfies id >= 10). Basic ownership mapping is established; no need to repeat elementary routing.
- Discussed OVF versus OOS and lifecycle implications of shared files. Coverage is not demonstrated mastery.
- Learner proposed inserting OOS only after partition selection, then agreed that the open design issue is avoiding the PR's full inline probe rather than changing per-heap ownership.
- Current: lesson 0004 traces exactly what partition selection consumes. Full-record transport versus single-attribute semantic dependency, value finalization, expression evaluation, and representation-ID side effects are the focus.
- HTML/SVG for sections 3 onward remains pending consolidation; do not claim generated artifacts are current with this discussion.

## Evidence boundaries

- Original book/source is pinned to b871ea386d2c5419b7abae07dda58b9b7f36377a. Lesson 0005 explicitly studies the local committed delta to 213ce80f54dc54130fcef22e616cb28f4835f6d5; older probe/rebuild chapters are historical context, not the new implementation.
- Separate implementation observations from accepted OOS requirements and design alternatives.
- No new runtime experiments, engine edits, commits, or pushes authorized by this teaching request.
