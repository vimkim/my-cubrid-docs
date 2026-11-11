# CBRD-27761: bestspace whole-heap free-space map

[CBRD-27761](https://jira.cubrid.org/browse/CBRD-27761) (Improve Function/Performance; relates to CBRD-26857, CBRD-27213, CBRD-27325, CBRD-27261). No PR is linked here yet. Source evidence: develop `e64a04a79`, which includes the CBRD-27325 rediscovery (`604ab8b22`, PR #7887).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [comment-develop-repro.md](comment-develop-repro.md) | Korean comment, posted as [comment 4778313](https://jira.cubrid.org/browse/CBRD-27761?focusedCommentId=4778313#comment-4778313) on 2026-11-11: a range DELETE and reinsert on develop `e64a04a79` grew the heap from 7,273 to 10,639 pages at a constant 240,000 rows; the candidate-queue drop and the 1,024-page rediscovery budget as the cause | 2026-11-11 | 2026-11-11 | Add develop evidence to the existing issue instead of filing a duplicate |
