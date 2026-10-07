# Durable ticket 02 evidence copy

Source: `/home/vimkim/tmp/pr7925-ticket02-evidence`, sealed after final verification.
The original report and evidence manifest are copied without changes. The report
SHA-256 is `1ee13e061ce24dd5483ae8b5d76e5bed4258b84528af6c30df6057154dbf8541`;
the original manifest SHA-256 is
`855ef7bbbb0c09a2447fbaa359e8d37470ca816807a5b6aa59cafd24bd860804`.

Build/runtime receipts, XML, audits, scripts, reviews, source diffs, configuration,
registry/creation metadata and retained-artifact inventory are committed here.
Generated `*.objects` benchmark inputs remain at their original paths and can be
reconstructed by the copied `benchmark.py`. Their paths, sizes and hashes are
listed in [generated fixture manifest](generated-fixtures.json); identical phase
hashes are checked in `benchmark-summary-final.json`. Python bytecode is omitted.
The original evidence manifest includes original bulk inputs and therefore is a
seal of the source evidence, not a claim that every original file is copied here.
No database volume, build directory, installation, socket, or retained native data
was copied or deleted by this operation.
