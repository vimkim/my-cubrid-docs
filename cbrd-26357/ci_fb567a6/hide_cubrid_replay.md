# Why hide_cubrid_replay missed the password mask

**The failed assertion received an empty result instead of `******`. The testcase has broken user setup and a timing-sensitive process sampler.** The setup defect is confirmed; the explanation that the sampler missed the shortened process lifetime is strongly supported but cannot be proven from the retained `ps` data, which is absent.

## What the test intended to check

The test launches `cubrid_replay` with a password and repeatedly runs `ps` in the background. It expects to observe stars in the command line after the tool masks the password. Assertion 7 checks user `qa9`; the [answer file](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/c4b9d482fbd491a68510b2552df2c3cac91911fc/shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/qa9.answer) contains exactly `******`.

## The failure sequence

1. The fixture calls `add_user` on class `db_user` to create users including `qa9`. The CI log reports `Method "add_user" not found`, then `wu1 is not defined` and `User qa9 is not in the database`.
2. The test continues despite these setup errors. The `qa9` replay reports `cci connect error`.
3. The comparison reports `1d0` followed by `< ******`: the expected mask line is absent, with no replacement line in the actual result. Only assertion 7 fails; the other ten comparisons pass.

The [fixture](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/c4b9d482fbd491a68510b2552df2c3cac91911fc/shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/create_user.sql#L11-L22) targets a catalog view that does not expose `add_user`. At the tested engine revision, [`db_user` exposes only `find_user` and `login`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/object/schema_system_catalog_install.cpp#L2080-L2106); [`_db_user` and `db_root` install `add_user`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/object/authenticate_context.cpp#L315-L389). This explains the actual setup errors. These engine definitions are unchanged between the integrated develop baseline and the PR head.

## Why the missing sample is timing sensitive

The [sampler](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/c4b9d482fbd491a68510b2552df2c3cac91911fc/shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh#L11-L33) starts a background `ps` loop, runs the replay, reads `ps.txt`, and only then kills the sampler. There is no acknowledgement that the sampler is ready or has seen the masked process. It also deletes lines containing the original password before comparison. An empty result therefore means **no usable masked sample**, not proof that the password was exposed.

The engine [masks the argument while parsing `-p`](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/broker/broker_log_replay.c#L1547-L1551), before [the connection attempt, which exits on failure](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/broker/broker_log_replay.c#L195-L201). A missing user makes this execution take the early-error path, shortening the opportunity to observe the mask. That is the leading explanation for the empty sample. The exact `ps.txt`, `tmp.txt`, and `debug.info` contents are not in the collected text evidence, so distinguishing a completely missed process from a pre-mask-only sample is not possible.

The test's filtering would also discard a plaintext sample instead of directly failing on it. That is a separate weakness of the check; this failure does not prove a password leak.

## What retries explain

The current shard used `testcase_retry_num=0`. A retry could change process scheduling and obtain a mask sample while leaving the invalid user setup unfixed. Historical cached runs from September 21 and 23 already report this testcase as `NOK, TRY->1`, with one failed testcase in each shard summary. These are supporting history, not a matched experiment: their engine/testcase identities and failure signatures were not fully revalidated for this report. They show that the testcase was not newly red only after the observed no-retry setting.

## Attribution and next action

**Category:** confirmed fixture incompatibility plus probable sampling race. **PR relation:** unlikely for these defects. **Confidence:** high for the invalid fixture and empty comparison; medium-high for the early exit causing the missed sample. The testcase directory matches the merged testcase develop parent; the catalog definitions and replay implementation match engine develop `f1bd99ed43a134383bc0be1d766a6f121601a499`.

**Falsifier:** a retained `qa9` sample showing a correctly masked command before comparison would challenge the missed-sample explanation and require investigation of extraction/filtering. Successful creation of `qa9` in the exact fixture would contradict the setup chain, but the actual log explicitly reports its absence.

**Next action:** update user setup to a supported interface such as `CREATE USER`, fail immediately when setup or login fails, and make process observation synchronized and bounded. Check explicitly for plaintext exposure; do not filter it away. Preserve per-user samples and exit status before a controlled rerun. No testcase or engine changes are included here.

## Evidence scope

This report concerns [PR 7990](https://github.com/CUBRID/cubrid/actions/runs/36570256001), engine `fb567a629cdb390fff920542173fa36f454c74a0`, September 29, 2026, run `36570256001`, attempt `1`, shell shard `17`. The testcase is `shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh` at private testcase revision `c4b9d482fbd491a68510b2552df2c3cac91911fc`. The debug build reports `11.5.0.2637-fb567a6`.

Evidence was collected on October 1 with `cubrid-ci 0.2.0 (45944012aaaa, release)` and validated against the collector schemas, observation, checksums, identities and counts. [Evidence excerpts](evidence.md) preserve the relevant assertions. This is log and source analysis; no database testcase was rerun. [Main report](../ci_analysis_report_fb567a6_codex.md).
