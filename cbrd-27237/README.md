# CBRD-27237

Documents for JIRA [CBRD-27237](https://jira.cubrid.org/browse/CBRD-27237) "[OOS] rollback 된 UPDATE 의 옛 OOS 체인을 vacuum 이 삭제해 살아있는 행이 손상됨": evidence for choosing the fix approach. No PR exists yet. The issue analysis itself lives in [my-cubrid-jira](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CBRD-27237-oos-forward-walk-rollback-delete_dcbf09e_claude.md).

Last modified: 2026-11-03 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [CBRD-27237-fix-options-deep-dive_dcbf09e_claude.md](CBRD-27237-fix-options-deep-dive_dcbf09e_claude.md) | Deep dive on fix options A/B/C at feature/oos-merge dcbf09e: runtime probes (savepoint, concurrent update, relocated row, SQL abort paths), the spec-A crash window, a simple-C prototype, change scope, and the updated recommendation (A carried by postpone) | 2026-11-03 | 2026-11-03 | Give the owner evidence for the work-tracker 705 decision |

The [probes/](probes/) directory holds the three local probe commits as patches, so readers can rerun the runtime claims. Those commits were never pushed.
