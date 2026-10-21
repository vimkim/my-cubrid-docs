# Page-buffer self-study materials

Created: 2026-10-21. Last modified: 2026-10-21 (Asia/Seoul).

These offline lessons explain page identity, fix ownership, pool structures,
and the distinction between page access and durability. Claims use CUBRID
`f799e05d77d5300c6ea5753b4a6cc7caee6d8912`; they describe that revision.

Read the lessons in this order:

1. [Fix is an ownership protocol](lessons/0001-pgbuf-fix-is-an-ownership-protocol.html).
2. [Write latch is not durability](lessons/0002-write-latch-is-not-durability.html).
3. [One BCB, many lists](lessons/0003-one-bcb-many-lists.html).

Use the [question bank](reference/pgbuf-question-bank.html) for review and the
[fix contract](reference/pgbuf-fix-contract.html),
[structure map](reference/pgbuf-structure-map.html), and
[durability contract](reference/pgbuf-durability-contract.html) as reference
cards. The [page-buffer index](../README.md) lists the Markdown analyses,
course scope, and source references.

The `assets/` files support these documents: `course.css` supplies their shared
styles, the three SVG diagrams illustrate the contracts and pool structures,
and `retrieval.js` runs the lesson exercises. `reference/pgbuf-question-bank.md`
is the question-bank source; `assets/question-bank-template.html` supplies its
Pandoc HTML shell. Its asset URLs are relative to the generated document in
`reference/`.
