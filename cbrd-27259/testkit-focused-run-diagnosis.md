# Focused native testkit SQL run — failure diagnosis (CBRD-27259 worktree)

- Date: 2026-11-10
- Engine worktree: `/home/vimkim/gh/cb/CBRD-27259-storage-force-inline` (HEAD `6d6a01ef4`, PR #8416, base `feature/oos-merge`)
- Install: `/home/vimkim/.cub/install/CBRD-27259-storage-force-inline/debug_gcc` (commit_match=yes)
- testkit: `…/go-github-com-cubrid-systems-cubrid-testkit-cmd-testkit/f01005295d3f…/bin/testkit`
- Original driver: `…/a6601308-…/scratchpad/run-sql-attempt.sh`
- Fixed driver: `/mnt/nvme/data-5/tmp/claude-1000/-home-vimkim-gh-cb-CBRD-27259-storage-force-inline/4ab40b01-2575-419e-8407-3c2cac5a85c0/scratchpad/run-sql-attempt-fixed.sh`

## Result

The harness now works. Attempt `/home/vimkim/tk/d2` started master, broker, and the HA server inside the
containment. It executed `cbrd_26719_03_probe_overflow_tuple.sql` and produced a complete result tree
(runner exit 0). The verify step reports **FAIL: fail count is 1**. This is a real testcase verdict. It
is not a harness failure (see "Testcase verdict" below).

Fix that made the server start: run testkit with
`env -u CUBRID_CONF_FILE -u CUBRID_BROKER_CONF_FILE -u CUBRID_CUBRID_PORT_ID …`.

## Root causes (in order hit)

| # | Root cause | Evidence | Minimal fix | Belongs in |
|---|---|---|---|---|
| 1 | `testkit` on PATH is a mise shim. With `HOME=$ATTEMPT/home`, mise cannot find its config, so the shim does not resolve. | `…/a6601308-…/scratchpad/sqlrun/cbrd_25717_null_join_key/run.log:2`: `mise ERROR testkit is not a valid shim` | Invoke the absolute path from preflight `testkit=` (`"$TESTKIT"`), never bare `testkit`. | **Skill contract**: `testkit-focused.md` "Invoke the native family" uses bare `testkit` after `HOME=` is rewritten. The helper already prints the path. |
| 2 | Attempt path too long for `CUBRID_TMP`. CUBRID puts unix sockets there, and `sun_path` is limited to about 108 bytes. genlocale fails, then CQT NPE in `ConsoleDAO.addDb`. | `…/sqlrun2/cbrd_25717_null_join_key/run.log:5`: `The $CUBRID_TMP is too long. (/mnt/nvme/…/cubrid/tmp)` | Use a short attempt root (for example `/home/vimkim/tk/dN`). | **Helper**: `prepare-config`/preflight should reject an attempt dir whose `cubrid/tmp` + socket name exceeds the limit. **Contract**: state the short-path rule. |
| 3 | The install had no JDBC jar because the `cubrid-jdbc` submodule was not initialized. | `/home/vimkim/tk/s1..s4/run.log` (JDBC missing). Fixed: install now has `jdbc/cubrid_jdbc.jar`. | `git submodule update --init` and reinstall (done). | **Environment/build**. Optional helper check: preflight asserts `$CUBRID/jdbc/cubrid_jdbc.jar` exists for sql/medium. |
| 4 | `cubrid genlocale` compiles through ccache. Inside the user namespace the uid is 0, so ccache tries `/run/user/0/ccache-tmp` and fails. `libcubrid_all_locales.so` is then missing and the server cannot start. | `/home/vimkim/tk/s5/run.log:20`: `ccache: error: Failed to create directory /run/user/0/ccache-tmp: Permission denied` | `CCACHE_DISABLE=1` (or `CCACHE_TEMPDIR=$ATTEMPT/tmp`) in the testkit env. | **Contract** (add to the env block). Arguably **testkit** too: the containment could set `CCACHE_DISABLE`/`CCACHE_TEMPDIR` itself because it creates the uid-0 view. |
| 5 | **Workenv overrides leak into the attempt.** The cub-workenv exports `CUBRID_CONF_FILE`, `CUBRID_BROKER_CONF_FILE`, and `CUBRID_CUBRID_PORT_ID=41268`. CTP edits `$CUBRID/conf/cubrid.conf` (copied, `ha_mode=yes`, `cubrid_port_id=1822`) and decides on HA from that file, so it runs `cubrid hb start basic`. The `cubrid` binaries read `CUBRID_CONF_FILE` instead (`.cub-workenv/conf/cubrid.conf`: `ha_mode=off`, port 41268), so hb start refuses and no server process exists. `check_status` then waits on `changemode` 50 times. The broker also uses the workenv broker conf, not CTP's. | `/home/vimkim/tk/s9/run.log:57`: `The server was not configured for HA.` followed by `waiting for basic become active…` ×N and `checkDb failed: CQT cannot reach the database`. No `cubrid/log/server` dir in s9. `s9/cubrid/conf/cubrid.conf:53 ha_mode = yes` vs. `.cub-workenv/conf/cubrid.conf ha_mode=off`. Logic: `CTP/sql/bin/run.sh` `start_db()` (greps `$CUBRID/conf/cubrid.conf`, calls `cubrid hb start`) and `check_status()`. | Unset the three vars for the testkit process (`env -u CUBRID_CONF_FILE -u CUBRID_BROKER_CONF_FILE -u CUBRID_CUBRID_PORT_ID`). Proven by `/home/vimkim/tk/d2/run.log:57-60`: `start database basic` / `restart broker...` / `[INFO] slot0: server and broker up in 36s`. | **Skill contract + helper**, primarily. The contract's env block starts with `direnv exec .`, which re-exports exactly these variables, and its "rewrite at minimum" list omits them. Fix: drop `direnv exec .` or add `env -u` for every `CUBRID_*` override (safest: unset all `CUBRID_*` except `CUBRID_JAVA_HOME`, then set the attempt ones). The helper preflight should fail or warn when `CUBRID_CONF_FILE`/`CUBRID_BROKER_CONF_FILE`/`CUBRID_<PARAM>` are set or point outside the attempt `$CUBRID`. **testkit** could also reject them, as it already requires `CUBRID_DATABASES` inside `$CUBRID`. |

Notes:

- The original driver itself was otherwise correct (copying, fresh `databases`, prepare-config, verify).
  Its only defects are #4 (worked around) and #5 (missing `env -u`). It also inherits #2 if it is given a long path.
- Containment is `CLONE_NEWNS|NEWPID|NEWIPC|NEWNET` per slot (`cubrid-testkit/internal/contain/slot.go:84`),
  so CTP's `cubrid service stop` cannot reach servers outside the attempt. No outside server was touched.
- `/home/vimkim/tk/s9/cubrid/conf/cubrid.conf` still shows `ha_mode = yes` because that run aborted before
  CTP restored its saved conf (`run.sh:280`). In d2 the conf was restored after the run.

## Testcase verdict (d2): a real behavior change from this PR, not a harness issue

- Testcase source: `/home/vimkim/gh/cubrid-testcases/feature-oos-merge` (`feature/oos-merge`, 112 behind origin).
  The brief's `/home/vimkim/gh/cubrid-testcases/tc-pr-8416` **does not exist**, so the PR's TC branch was not used.
- Result dir: `/home/vimkim/tk/d2/CTP/sql/result/y2026/m11/schedule_linux_sql_64bit_1017242316_11.5.0.2796-6d6a01e`
- Diff `group/cbrd_26719/cases/…03_probe_overflow_tuple.result` vs `answers/…answer`:
  - line 10: `Error:-1388` vs `2000` (data insert rejected)
  - line 23: `0` vs `100` (count; follows from the rejected insert)
  - lines 47-51: plan shows `method: skip` / `noscan` with no parallel workers (empty table)
- `-1388` = `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (`src/base/error_code.h:1793`): "record … exceeds the maximum
  record size after moving eligible variable-length columns to OOS … A record must fit in one page."
  The case builds rows of eight `bit(32000)` columns (32,000 fixed bytes > one 16K page). Commit `abd2136f5`
  ("Reject every user-class record that would become REC_BIGONE") now rejects these rows on purpose.
- Implication: cbrd_26719_03 (and probably other cases that rely on fixed-width overflow rows) needs a TC
  update for PR #8416, for example by switching to variable-length wide columns that move to OOS. Re-run
  against the PR's TC branch once it is checked out.

## Recommended changes (not applied; need user approval)

1. `cubrid-common/references/testkit-focused.md` (source: `/home/vimkim/gh/my-cubrid-skills`):
   - Replace `direnv exec . env` with `env -u CUBRID_CONF_FILE -u CUBRID_BROKER_CONF_FILE -u CUBRID_CUBRID_PORT_ID`
     (or a full `CUBRID_*` scrub). Add these vars to the "rewrite every install-bound runtime variable" list.
   - Use `"$TESTKIT"` (the preflight `testkit=` path), not bare `testkit`.
   - Add `CCACHE_DISABLE=1` to the env block.
   - Require a short attempt root and explain the `CUBRID_TMP` socket-path limit.
2. `testkit-focused.py`: preflight checks for leaked `CUBRID_CONF_FILE`/`CUBRID_BROKER_CONF_FILE`/`CUBRID_<PARAM>`
   overrides and for the `CUBRID_TMP` length; optionally a JDBC-jar presence check.
3. cubrid-testkit (optional hardening): in contained runs, reject or scrub conf-file overrides that point outside
   `$CUBRID`, and set `CCACHE_TEMPDIR` or `CCACHE_DISABLE`.
4. Environment: keep the JDBC submodule initialized in installs (done).

## Attempts

| Attempt | Outcome |
|---|---|
| `…/a6601308-…/scratchpad/sqlrun/*` | failed: mise shim (#1) |
| `…/a6601308-…/scratchpad/sqlrun2/*` | failed: CUBRID_TMP too long (#2) |
| `/home/vimkim/tk/s1..s4` | failed: JDBC missing (#3) |
| `/home/vimkim/tk/s5..s8` | failed: ccache tmp (#4) |
| `/home/vimkim/tk/s9` | failed: workenv conf/port override (#5) |
| `/home/vimkim/tk/d1` | aborted: testcase path `tc-pr-8416` does not exist (no testkit run) |
| `/home/vimkim/tk/d2` | harness OK, runner exit 0; verify FAIL (1 case failed: -1388, real verdict) |

## Follow-up (2026-11-11)

- Recommended changes 1-2 were applied in my-cubrid-skills commit `71f1cb0` ("fix(common): make focused testkit runs
  work from a cub-workenv worktree"). It was pushed to origin/main and the installed copy matches the source. It adds
  the preflight `env_unset=` line, `CCACHE_DISABLE=1`, the absolute `"$TESTKIT"` path, the JDBC-jar check, and the
  96-character `CUBRID_TMP` limit in prepare-config.
- Passing proof: `/home/vimkim/tk/s11` ran cbrd_26719_03 from TC `tc/pr-8416` at `d7b1d3a3c` and passed verify with
  total=1 and success=1 (install 6d6a01e). The d2 `-1388` failure came from the old pre-PR case on `feature/oos-merge`.
