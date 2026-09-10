# Mission: Understand and evaluate PR #7600

## Why

Read PR #7600 line by line and independently evaluate its storage ownership and write-preparation design. Build enough foundational understanding to compare alternatives instead of accepting the existing implementation as the only possible design.

## Success looks like

- Explain partition selection and distinguish a logical table, partition heap, file, and page.
- Trace heap/OVF/OOS ownership through the pinned source.
- Explain the inline probe/rebuild path and distinguish baseline work from added work.
- Compare shared and per-partition storage, separating correctness requirements, historical choices, and unmeasured performance hypotheses.

## Constraints

- One small concept per interaction; check understanding before advancing.
- Agent researches implementation facts; learner is not expected to supply them.
- Preserve findings in Markdown; update HTML/SVG after each section is settled.
- No engine changes or experiments without a new explicit request.
- Use this directory as the learning workspace; existing book coverage is not proof of learning.

## Out of scope

- Implementing an alternative design or publishing additional changes automatically.
- Broad subsystem study unrelated to understanding this PR.
