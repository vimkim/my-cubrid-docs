# Content and presentation audit — 2026-09-08

The analysis verifier passed with 57 source facts, 1 runtime observation, 4 inferences and 2 explicit unknowns. The generated appendix covers 30 hunks, 306 added lines and 23 deleted lines in all six PR files. Git extraction checks those files against the pinned head before every build.

Decisive code was reopened for owner forwarding, suppression in both layout branches, final-pass increment seeding, LOB state transitions, lower-locator pruning, the test bridge, MVCC reevaluation's ordinary-mode call, and the vacuum lookup return contract. The source map distinguishes the base from the head when describing old behavior.

The large locator, wrapper and regression hunks include statement-sized line guides in addition to numbered source. No changed hunk is omitted. Brace/blank/signature lines remain visible and their structural role is explained alongside the executable changes.

Two reconciliations remain prominent in the narrative: normative versus pinned ordinary OOS threshold, and historical crash description versus current true-with-null lookup behavior. The current-server inconsistent-owner failure path (C-013) and runtime coverage beyond the selected regression (C-032) remain open. No corruption injection, full-suite rerun, restart or backup success is claimed.

The isolated SA regression passed using the existing binary whose SHA-256 is recorded in regression.json. The database and copied configuration are retained in the private sandbox recorded there. No shared registry or configuration was targeted, and the test shut down its in-process engine.

Static HTML/anchor/resource checks passed. Chromium opened the full book at 1280px and 390px with networking disabled, then opened all ten chapter pages. No page overflow, broken image, out-of-viewBox SVG text, network resource or JavaScript error was observed. Answer and evidence-link navigation worked. Print styling uses a white background and no remote resource.

Desktop, phone, call-flow and annotated-diff screenshots were inspected. TOC numbering and diagram arrows were corrected before final verification. Wide figures/tables/code intentionally scroll within their panels on narrow screens.

Two consecutive renderer runs produced byte-identical index.html; reproducibility.json records the hash. Build dependencies and commands are in README.md. The deliverable is ready within the declared teaching scope; the learner's progress remains unassessed.
