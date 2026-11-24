# CBRD-28032

Bitmap heap scan and batch join: heap lookups of an index scan in file order, and the inner heap pages of a nested-loop join prefetched ahead.

Related PRs: [CUBRID/cubrid#8627](https://github.com/CUBRID/cubrid/pull/8627) (engine, author `xmilex-git`).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr8627-review.md](pr8627-review.md) | Code review of PR #8627 at head `b52b26697c`: confirmed P1 defects `F-1` and `F-2`, non-blocking source risks, and storage/OOS/VACUUM checks | 2026-11-24 | 2026-11-24 | Review PR #8627 and record blocking changes-required evidence |
