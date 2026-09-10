# Ticket 01: activation and compatibility verification

Status: ticket 01 completed and committed as `9960c7fc6` on `CBRD-26939-oos-cdc`, based on merged source `f4299ac0c`. Build, all three lifecycle matrices, and all 27 configured tests passed. This is not completion of the full CDC/OOS feature.

## Implemented behavior

- Fresh databases use disk compatibility11.6; fixed engines retain11.5 support without implicit activation.
- `cubrid activatehistorydb` initializes parameters, enforces the exclusive active-log lock, requires clean shutdown, preserves other header bytes/data/history, and flushes the format fence before success.
- Startup synchronizes current-format compatibility before recovery, including an interrupted activation whose marker only reached the OS cache. Routine fsync suppression cannot bypass this fence.
- Inactive supplemental OOS writes fail before row mutation, checking old/new images including relocation/overflow paths. Normal supplemental-off writes and non-OOS history remain usable.
- Backups and credentials use the actual database compatibility. Copied-log readers validate supported compatibility. Independent old readers still require coordinated replacement.
- New error definitions are mirrored into the CCI header. dbi_compat.h includes the engine error header already.
- Linux scope; user explicitly confirmed Windows is unsupported.

## Verified results

| Check | Result | Evidence under `/home/vimkim/.cache/cubrid-history/` |
| --- | --- | --- |
| Complete public lifecycle at4KB data/log pages | PASS | `run.Qamwd9/` |
| Complete public lifecycle at8KB data/log pages | PASS | `run.xXgVK9/` |
| Complete public lifecycle at16KB data/log pages | PASS | `run.1SfSuM/` |
| Configured build and test suite | 27/27 PASS, 130.34 seconds | `ctest.OeKccw/build-test.log` |
| GNU indent2.2.11 and whitespace checks | PASS; no unrelated formatting drift | Source diff/review |
| Standards review | No remaining findings within Linux scope | Independent reviewer, current session |
| Spec review | Two test gaps filled; no remaining findings | Independent reviewer, current session |

The lifecycle matrix includes baseline open rejection for fresh/activated/restored-current databases; inactive open and baseline backup restore; SA/CS INSERT/UPDATE/DELETE refusal and unchanged rows; running/unclean activation refusal; non-OOS flashback SQL equality before/after activation; copied-log reader acceptance; current backup restore; process termination before/after write and sync; write and sync I/O errors; and direct startup after interruption with a failing fence sync followed by successful recovery. An injected startup sync failure follows CUBRID's existing fatal log-init path (debug process abort); it is an expected fail-stop, followed by successful normal startup and preserved data.

## Review corrections

The first fresh-database regression failed on the real baseline binary, then passed with the new compatibility rule. The inactive-backup regression caught engine-default stamping and passed after recording the actual database level. The OOS write regression caught silent legacy publication and passed with the guard. The syscall test caught skipped activation fsync under suppression and passed after the unconditional fence was added.

Review added explicit baseline rejection after restoring a current backup, and direct-startup failure injection before any activation retry. Both pass at all three page sizes.

## Concurrent merge and preservation

At final commit time, another process had started merging origin/develop14d21ef51 into feat/oos and autostashed the implementation. The merge/index were left untouched. The verified tracked edits are preserved in autostash6de258c1037c56c008ddd0ee1ad9aa923ce149a5 and exported to `ticket1-recovery/engine.patch`. That directory also contains the CCI patch and independent copies of the final test scripts/operator document.

The merge completed as f4299ac0c and restored the implementation. The two activation error numbers are now -1385 and -1386, consistently updated in engine/messages/CCI/docs. Review found no new interactions with the merged CDC archive watermark; activation preserves the complete stored header except compatibility. The rebuilt merged source passed the lifecycle matrix above.

CCI companion commit: `76b293743800620cc521fb818b9567b6ae19cad9`, based on the canonical pinned CCI revision `bd86063a5bd481f0e22bf07c8a76bf736f86443a`. The engine commit records that descendant, preserving the user's preexisting nested CCI checkout and Windows version-file edits. Publication must make this companion commit available before publishing the engine gitlink. The engine and CCI branches are now published for draft PR #7897.

## Branch correction

At the user's request, moved unchanged commit `9960c7fc6` to branch/worktree `CBRD-26939-oos-cdc`. Restored local `feat/oos` to `f4299ac0c` with a keep reset, preserving unrelated local files and nested submodule edits. Future implementation belongs in `/home/vimkim/gh/cb/CBRD-26939-oos-cdc`. Draft PR: https://github.com/CUBRID/cubrid/pull/7897 (base `feat/oos`). Fresh recursive submodule checkout succeeded through the configured canonical URLs.
