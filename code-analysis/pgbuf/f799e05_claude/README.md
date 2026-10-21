# CUBRID page buffer: presentation and evidence corpus

Created: 2026-09-01. Last modified: 2026-10-21 (Asia/Seoul).

Seminar package for `src/storage/page_buffer.c`, using CUBRID
`f799e05d77d5300c6ea5753b4a6cc7caee6d8912`. Live monitoring used that revision
plus logging-only probes on
[`page-buffer-survey-with-tracers`](https://github.com/vimkim/cubrid/tree/page-buffer-survey-with-tracers),
probe commit `75d64f959`.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CUBRID_PAGE_BUFFER_PRESENTATION_KO.md](CUBRID_PAGE_BUFFER_PRESENTATION_KO.md) | Korean presentation, caller contracts, and reviewer Q&A | 2026-09-01 | 2026-10-21 | Explain the page lifecycle to teammates |
| [analysis/README.md](analysis/README.md) | Navigation for the source and runtime evidence notes | 2026-09-01 | 2026-10-21 | Connect presentation claims to detailed evidence |

The presentation links its [state-axis diagram](presentation-assets/page-buffer-state-axes.svg)
and [caller-contract diagram](presentation-assets/pgbuf-contract.svg). The
[topic index](../README.md) lists every important Markdown document in this corpus.
