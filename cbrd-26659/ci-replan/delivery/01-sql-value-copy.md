# Ticket01: compact SQL value-copy delivery

Date: 2026-10-08 (Asia/Seoul). Status: Ticket01 logical delivery verified and committed; physical companion credit remains separate. Parent CBRD-26659, work tracker 306. Engine source `fb567a629cdb390fff920542173fa36f454c74a0`; coordinating branch has no associated PR. Implements [approved Ticket01](../tickets/01-sql-value-copy.md) at the already approved normal SQL/JDBC seam. No engine change or publication is included.

## Delivered behavior and independent oracle

Public worker `/home/vimkim/gh/cubrid-testcases/oos-01-sql-value-copy`, branch `task/oos-01-sql-value-copy`, fixture commit `5e25be4e2d1d471b1f1b3ea6736c970f8c323e34`, based on public integration `bdba62aee0faec05abdd861518824c69b6c1b3c5`. Exact pair:

- `sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql01_insert_select.sql`
- `sql/_36_guava/cbrd_26659/answers/cbrd_26659_oos_sql01_insert_select.answer`

The recovered P03 INSERT SELECT structure is prior art. Four compact ordered rows replace its 100/1000-row scale variants. Each payload has three distinguishable byte segments; each tag differs across rows and from its payload. The independent length and complete MD5 oracle prevents equal-length substitutions, reordered segments and tail truncation from passing only an aggregate/equality check.

| id | Payload bytes, in order | Tag bytes | Payload octets | Serialized disk size | Expected payload MD5 |
| --- | --- | --- | ---: | ---: | --- |
| 1 | aa*1000 + bb*1000 + cc*1000 | 11*300 | 3000 | 3008 | 4d99190ee568772b70b0244abddbaa00 |
| 2 | d1*1401 + e2*1403 + f3*1403 | 22*300 | 4207 | 4212 | 5a43433dc26414a3625551ee8fc23cd2 |
| 3 | 12*7001 + 34*6501 + 56*6501 | 33*300 | 20003 | 20008 | 127967dc901ebb2776d754d2257cadf3 |
| 4 | 78*11001 + 9a*11000 + bc*11000 | 44*300 | 33001 | 33008 | ec5759eaa4472233734552dfd216c552 |

Every recipe unit is one byte represented by two hex characters. Payload total is `3000+4207+20003+33001=60211`; tags total 1200 octets and each serialized tag is 308 bytes. For this VARBIT fixture, disk size is `ceil((5+N)/4)*4`; MD5 is independently calculated as `hashlib.md5(hex_text.encode('ascii')).hexdigest()`. The distinct complete digests count is 4 and payload/tag alias count is 0.

The small metadata table records only pattern/count recipes. Source id1 uses VALUES; ids2..4 use INSERT SELECT from metadata. A second table copies source via INSERT SELECT. Tests 1/2 check ordered source values, whole lengths/digests and row-by-row source/model equality. Test 3 DELETEs all source rows, expects source count 0 and retained exact copied values. Test 4 DROPs source and repeats every copied-row value check plus total 60211. Test 5 DROPs copy/model and expects zero catalog entries for all three exact fixture names. Default JDBC autocommit=true; the case changes no session parameter, trace or trigger state.

The answer was derived before execution. Reviewable recipe/model and root's independent byte reconstruction are retained at:

- `/home/vimkim/tmp/oos-developer-regressions-20261008/ticket01/oracle-review.md`
- `/home/vimkim/tmp/oos-developer-regressions-20261008/ticket01/independent-model.json`
- `/home/vimkim/tmp/oos-developer-regressions-20261008/ticket01/root-oracle-review.md`

Root accepted the logical state and literal oracle before runtime. SQL SHA-256 `a6ba6470013fd90d6bd9bf324e04ba7c0024bcf1ce872d34324f6036773d1803`; answer SHA-256 `7aa5bb764b05607e5edf9f53f04fa909922875d167342c48d003ab151e8d3e23`. Neither answer was generated from actual engine output.

## Native execution procedure and identity

Reusable retained procedure, outside tracked repositories: `/home/vimkim/tmp/oos-developer-regressions-20261008/native-sql-attempt.py`. It accepts repeated `--case` identities for later exact SQL selections, copies containing cases/answers/fixtures into a fresh immutable attempt, clears discovery of unselected case siblings, checks tracked source/answer existence and prepares an exact positive manifest. It copies the engine and CTP assets, preserves the copied registry and creates a new empty attempt registry and internal TMP. Use a short whole-attempt prefix so native slot socket paths fit Linux UNIX socket limits. Runtime HOME/config/TMP/install/CTP/JDBC paths are bound explicitly with a clean environment, and the public/private roots are recorded. It never selects an engine from ambient direnv state.

```bash
python3 /home/vimkim/tmp/oos-developer-regressions-20261008/native-sql-attempt.py \
  --attempt /home/vimkim/tmp/oos306-sql01-ATTEMPT \
  --source /home/vimkim/gh/cb/CBRD-26659-oos-testcases-handover \
  --install /home/vimkim/.cub/install/CBRD-26659-oos-testcases-handover/optdebug \
  --ctp /home/vimkim/gh/ctp/run-sql/CTP \
  --java /home/vimkim/.local/share/mise/installs/java/temurin-8.0.462+8 \
  --public-root /home/vimkim/gh/cubrid-testcases/oos-01-sql-value-copy \
  --private-root /home/vimkim/gh/cubrid-testcases-private-ex/oos-regressions-integration \
  --case sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql01_insert_select.sql
```

Use a new ATTEMPT path for every invocation. Ticket01's red run adds `--wrong-first-total`, changing only the first copied answer 60211 to deliberately false 60212. Preparation preserves the native SQL configuration's JDBC/HA/server/broker/locale settings, sets one slot, clears exclusions and explicitly sets createdb page sizes 16K and DB/log volumes 64MiB: `--db-page-size=16K --log-page-size=16K --db-volume-size=64M --log-volume-size=64M`. The smaller volumes are an authorized disposable setup choice for this 60KiB fixture, independent of logical/OOS behavior. `[sql] jdbc_config_file=test_default.xml` uses the default JDBC executor with autocommit=true; source 11.5 selects `en_US.utf8`. Native invocation is exactly `TESTKIT_NATIVE=sql TESTKIT_CONTAIN=1 testkit sql -c <attempt>/conf/sql.conf`. TESTKIT_SLOT_VOLATILE stays unset. An exclusive coordination `validation.lock` covers copying/config preparation, preflight, native runner, verification and normal cleanup; lock waiting is excluded from all measured phases. Preparation and verification overhead are recorded separately from native runner elapsed, which includes database/locale/JDBC fixture setup and normal teardown. The normal runner restores engine/broker/HA configuration; the driver records and restores the locale preparation file separately. The `cleanup-owned-sql-attempt.py --attempt <path>` companion safely completes failed setup cleanup under the same lock after proving no attempt-native process survives; it uses isolated native deletedb, preserves generated fixture leftovers outside runtime and records parameter/TMP cleanup. Neither procedure performs a global host cleanup.

Shared build/install preparation is owned by root: 129.45s, separate from testcase timings. Source-matching OptDebug `cubrid_rel` is `11.5.0.2637-fb567a6`; JDBC source pin `71d7dfeef93eb788f8b03b7bd21a9e4974a7a7c0`, jar SHA-256 `0f5e56c7eaed0ebeb1eba3a8bba5a5db513e7eec455498d268e2205d48c02576`. Native binary `/home/vimkim/.local/bin/testkit` reports `cubrid-testkit dev`, SHA-256 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`. Its known modified-build provenance remains a reproducibility limit. CTP assets HEAD `9c62858b10005d721546cc007be260844033b9e9` contain preexisting helper modifications; attempt identities retain their dirt. JDK8 reports `javac 1.8.0_462`.

## Retained attempts and observed verdicts

All receipts/logs remain outside Git. Coordination links at `/home/vimkim/tmp/oos-developer-regressions-20261008/ticket01/` point to short attempts04/05. Earlier long-prefix attempts are preserved in that same directory.

| Attempt | Actual result | Native runner elapsed | Case body | Cleanup/evidence |
| --- | --- | ---: | ---: | --- |
| `attempt-01-wrong-answer` | Setup-inconclusive; missing `ip` from explicit PATH, zero executed cases |59.00s |Not executed |Added `/usr/sbin:/sbin`; isolated native deletedb=0, internal DB removed, empty registry, original configs restored; Java fixture leftovers retained outside runtime |
| `attempt-02-wrong-answer` | Startup-inconclusive; long broker/PL UNIX socket path, zero executed cases |302.82s |Not executed |Retained native failure logs; owned processes exited naturally; native deletedb + config cleanup proven in `owned-cleanup-final.json` |
| `attempt-03-wrong-answer` | Startup-inconclusive; native slots override external short TMP with long install/tmp, zero executed cases |291.73s |Not executed |Retained long-socket logs and unused external TMP ownership; owned processes exited naturally; failed cleanup complete |
| `/home/vimkim/tmp/oos306-sql01-a04` |Verified negative control: exact1 executed, native NOK1, helper rejects despite runner exit0 |88.69s |121ms |`negative-control-proof.json`: actual output equals independently reviewed correct answer and differs solely from the deliberately mutated first total60212; normal teardown and parameter cleanup pass; locale restoration0.10s |
| `/home/vimkim/tmp/oos306-sql01-a05` |Verified clean pass: exact1 executed/success1, fail0, skip0; helper exit0 |84.07s |118ms |Native stop/deletedb after results, empty registry, basic directory absent, no owned native process, runtime configs restored; auxiliary locale restored and fresh internal TMP retained outside runtime |

Attempts01/02 copied/prepared before the later stricter serialization rule. Attempt02's elapsed is retained with possible overlap from Ticket02's preparation and is not a final cost estimate. Attempts03/04/05 serialize copying and runtime together; final clean cost comes from05. Recorded preparation costs01..04 are1.25/1.11/1.09/1.03s. Shared build129.45s remains separate.

The socket failure is a runner/environment limitation, not an engine-value defect: native `slotTmp` validates the short master leaf `/CUBRID65535`, then replaces the caller's TMP with install/tmp, whose longer broker/PL socket names exceed 108 bytes under the original deep attempt prefix. A short complete retained install prefix fixes the invocation without engine/runner changes, JavaSP disablement, CTP fallback or weakened expectations. Attempt03 therefore receives no red-test credit. The current driver rejects long prefixes before DB execution.

Negative04 completed every SQL statement, including final `fixture_tables=0`, and emitted result `.result`, `summary_info`, `main.info`, summary/JUnit XML and exact absolute executed identity. Required helper rejects its single native failure. A separate independent proof compares the actual rendering to the original reviewed answer after restoring only 60212 to 60211 in the disposable wrong answer; it finds no other difference. The committed answer remains unchanged.

Clean05's required helper verifies the exact copied case identity `/home/vimkim/tmp/oos306-sql01-a05/testcases/sql/_36_guava/cbrd_26659/cases/cbrd_26659_oos_sql01_insert_select.sql`, all-success `summary_info`/`main.info`, `summary.xml`, `linux_sql_*.xml` and per-case `.result`. Result root is `/home/vimkim/tmp/oos306-sql01-a05/CTP/sql/result/y2026/m10/schedule_linux_sql_64bit_0818340976_11.5.0.2637-fb567a6`. The before-run identity manifest and `post-run-hashes.json` confirm identical source/copied SQL/answer hashes after execution. No answer formatting/coercion correction was needed.

Clean05 runner elapsed 84.068s includes native locale/JDBC fixture/DB setup, actual SQL and normal teardown; locked preflight+runner+verification+cleanup elapsed 84.573s. Preparation is separately measured at 1.028s in `preparation-time.json`; the summed measured preparation and locked invocation intervals are 85.601s, excluding lock waiting. SQL body 118ms is reported separately rather than confused with whole-suite cost. A single compact case has been measured; no whole 14-ticket selection or company-worker timing claim follows.

Normal teardown is distinguished from the initial setup clean by requiring post-`Result Root Dir:` stop/delete messages. Every actual case reaches catalog `fixture_tables=0`; CQT exits/closes its JDBC connection, native slots close and native do_clean deletes the prepared database. All three runtime config hashes match their copied pre-run baseline. Native make_locale changes its auxiliary locale-selection file; the driver retains the post-clean version and restores its copied original, recording that separate action. The fresh short internal TMP directory and its inactive files are retained outside executable runtime at `runtime-tmp-retained`, and the original path is absent. The process scan records inaccessible/racing host PIDs and does not claim global host inactivity; every observed process associated with this exact attempt install is gone. Failed-attempt receipts separately preserve pre-clean settings and native deletion evidence. No host registry, original Debug environment, shared install parameters, preexisting socket or unrelated process was changed.

## Proof scope and coverage handoff

SQL proves logical VALUES/INSERT SELECT/read/copy independence for the four modeled rows. It receives no physical-placement credit. Ticket02 receives the exact schema/recipes and public SQL hash for a companion's own CS16KiB fixture: id1 and tags are intended to stay inline, ids2/3/4 payloads are intended for 1/2/3 chunks. With 24-byte chunk headers the positive expected slot-record total per live owner file is `4212+20008+33008+6*24=57372`. Source's max chunk payload 16280 bytes yields 6 chunks. A quiescent companion must independently identify positive owner/file/count/byte evidence; it does not observe the actual SQL invocation.

Coverage delta for the integration owner: R01 logical VALUES/INSERT SELECT source and copy, exact ordered model preservation through source DELETE/DROP; R05 limited logical mixed single/two/three-chunk-sized values with distinct segments. R01 physical owner/activation and R05 actual chunk placement remain credited only to passing companion observations. No boundary, many-attribute, retry, raw-consumer call path, vacuum/reclaim, snapshot, rollback, crash or HA claim is added. No known engine defect is encoded as a successful expected result.

Focused checks: native red/green proofs described above, explicit tracked case/answer discovery, independent oracle review, Python procedure compilation, exact source/answer hash verification, and scoped Git whitespace checks. CQT answer trailing spaces/final blank line intentionally follow neighboring renderer conventions; the SQL/document diff passes the corresponding check. The public worker merges the current integration branch before handoff; only the case/answer pair is changed and the checkout is clean.

No mandatory Ticket01 criterion remains unmet. Remaining limits are separately tracked physical placement/ownership credit, broader representation/read/write/lifetime behaviors, and the documented native runner socket-prefix limitation. The root/merger owns updates to shared coverage.md and README. This report is the only durable Ticket01 documentation change; raw scripts, models, receipts and logs remain outside the repository.
