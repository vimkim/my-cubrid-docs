# CBRD-28035

Documents for JIRA [CBRD-28035](https://jira.cubrid.org/browse/CBRD-28035): every NEXT VALUE on a serial whose comment is in OOS writes a new OOS chain and leaves the old one unreclaimed. The issue draft lives in [../cbrd-27781/jira-drafts/CBRD-28035-serial-next-value-oos-chain-leak.md](../cbrd-27781/jira-drafts/CBRD-28035-serial-next-value-oos-chain-leak.md). Engine branch `CBRD-28035-serial-oos-chain-leak` over `feature/oos-merge` `67220b7e23`.

Last modified: 2026-11-11 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [pr-body.md](pr-body.md) | PR body (Korean), as published on draft PR CUBRID/cubrid#8492 at `bee96e666` | 2026-11-11 | 2026-11-11 | Draft PR against `feature/oos-merge` |
| [pr-body-rev2.md](pr-body-rev2.md) | PR body revision 2 (Korean): keep the unchanged OOS chain, at `7e9a4a513` | 2026-11-11 | 2026-11-11 | Review finding: eager reclaim races non-fixed scans |
| [race-repro.md](race-repro.md) | Reproduction (Korean) of the NEXT VALUE vs non-fixed scan race: procedure and results for base, eager reclaim, and keep-chain builds | 2026-11-11 | 2026-11-11 | Evidence for the design change in PR #8492 |
| [pr-context.md](pr-context.md) | Draft context: source commit, base, authorization, operations, execution record | 2026-11-11 | 2026-11-11 | Resume and publication bookkeeping |
