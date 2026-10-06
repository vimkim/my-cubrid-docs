# Exact-commit failure excerpts

These excerpts preserve the concise diagnostics from the validated messages. Repeated shell tracing is omitted. Full messages and all hashes remain in the evidence bundles.

## tested: `shell/_06_issues/_16_2h/cbrd_20683/cases/cbrd_20683.sh`

Source: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/f037616cd17af92e1226afcde80fd2a6fff9121d/providers/github-actions/runs/37463915181/attempts/1/test_shell/failures/shell_06_issues_16_2h_cbrd_20683_cases_cbrd_20683_sh-19eef560aa/message.txt`

```text

EnvIdentify: EnvId=local[parallel-04]
Hostname: cubrid-arc-586zc-runner-ghnw5-workflow
cbrd_20683-1 : OK
cbrd_20683-2 : NOK
diff volume.log volume_1.answer failed
22:23:26----/home/cubrid-testcases-private-ex/shell/_06_issues/_16_2h/cbrd_20683/cases--- time=6

242: < PERMANENT           PERMANENT DATA                8            20.5 M             603.5 M              624.0 M
244: > PERMANENT           PERMANENT DATA                8            20.2 M             603.8 M              624.0 M
246: < -                   -                            10            21.0 M             635.0 M              656.0 M
248: > -                   -                            10            20.8 M             635.2 M              656.0 M
250: <     0               PERMANENT           PERMANENT DATA         18.8 M             493.2 M              512.0 M         /home/cubrid-testcases-private-ex/shell/_06_issues/_16_2h/cbrd_20683/cases/db20683
252: >     0               PERMANENT           PERMANENT DATA         18.5 M             493.5 M              512.0 M         /home/cubrid-testcases-private-ex/shell/_06_issues/_16_2h/cbrd_20683/cases/db20683
```

## tested: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh`

Source: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/f037616cd17af92e1226afcde80fd2a6fff9121d/providers/github-actions/runs/37463915181/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt`

```text

EnvIdentify: EnvId=local[parallel-46]
Hostname: cubrid-arc-586zc-runner-gq8pz-workflow
cbrd_27064-1 : OK  insert overflow regression
cbrd_27064-2 : NOK
===== delete overflow (type=2 expected=700) =====
EXTRACT_START: start_lsa=373798769071760750 waited=3s target_type=2
EXTRACT_ERROR: rc=-10 target=10
TARGET_COUNT: 10/700 type=2
DML_TOTAL: 162
INSERT_COUNT: 152
UPDATE_COUNT: 0
DELETE_COUNT: 10
EXTRACTOR_RC=1 (124=hang/timeout)
CORRUPTION=0  TARGET_COUNT=10/700
cbrd_27064-3 : NOK
===== update overflow round 1/3 (type=1 expected=2400) =====
EXTRACT_START: start_lsa=189151184349574859 waited=6s target_type=1
EXTRACT_ERROR: rc=-10 target=4
TARGET_COUNT: 4/2400 type=1
DML_TOTAL: 5
INSERT_COUNT: 1
UPDATE_COUNT: 4
DELETE_COUNT: 0
EXTRACTOR_RC=1 (124=hang/timeout)
CORRUPTION=0  TARGET_COUNT=4/2400
22:26:46----/home/cubrid-testcases-private-ex/shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases--- time=113
```

## tested: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh`

Source: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/f037616cd17af92e1226afcde80fd2a6fff9121d/providers/github-actions/runs/37463915181/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt`

```text

EnvIdentify: EnvId=local[parallel-47]
Hostname: cubrid-arc-586zc-runner-ptvxw-workflow
cbrd_27075-1 : NOK
=== page size 4K (payload 20480 bytes) ===
config 4K: FINAL_SEQ=2000 CORRUPTION=0 DRIVER[FIND_OK=30 FIND_NOTFOUND=0 FIND_ERR=0 EXTRACT_ERR=1 TOTAL_ITEMS=292]
=== page size 8K (payload 40960 bytes) ===
config 8K: FINAL_SEQ=2000 CORRUPTION=0 DRIVER[FIND_OK=30 FIND_NOTFOUND=0 FIND_ERR=0 EXTRACT_ERR=0 TOTAL_ITEMS=292]
=== page size 16K (payload 81920 bytes) ===
config 16K: FINAL_SEQ=2000 CORRUPTION=0 DRIVER[FIND_OK=30 FIND_NOTFOUND=0 FIND_ERR=0 EXTRACT_ERR=0 TOTAL_ITEMS=290]
NUM_CONFIGS=3
CONFIGS_OK=2
TOTAL_CORRUPTION=0
22:27:30----/home/cubrid-testcases-private-ex/shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases--- time=239
```

## base: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases/cbrd_27064.sh`

Source: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0/providers/github-actions/runs/36570256001/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27064_cases_cbrd_27064_sh-1e79382118/message.txt`

```text

EnvIdentify: EnvId=local[parallel-29]
Hostname: cubrid-arc-586zc-runner-q9hvv-workflow
cbrd_27064-1 : OK  insert overflow regression
cbrd_27064-2 : NOK
===== delete overflow (type=2 expected=700) =====
EXTRACT_START: start_lsa=407575766277039475 waited=3s target_type=2
EXTRACT_ERROR: rc=-10 target=23
TARGET_COUNT: 23/700 type=2
DML_TOTAL: 178
INSERT_COUNT: 155
UPDATE_COUNT: 0
DELETE_COUNT: 23
EXTRACTOR_RC=1 (124=hang/timeout)
CORRUPTION=0  TARGET_COUNT=23/700
cbrd_27064-3 : NOK
===== update overflow round 1/3 (type=1 expected=2400) =====
EXTRACT_START: start_lsa=911978924542539255 waited=14s target_type=1
EXTRACT_ERROR: rc=-10 target=0
TARGET_COUNT: 0/2400 type=1
DML_TOTAL: 1
INSERT_COUNT: 1
UPDATE_COUNT: 0
DELETE_COUNT: 0
EXTRACTOR_RC=1 (124=hang/timeout)
CORRUPTION=0  TARGET_COUNT=0/2400
22:26:05----/home/cubrid-testcases-private-ex/shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27064/cases--- time=86
```

## base: `shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases/cbrd_27075.sh`

Source: `/home/vimkim/.local/share/cubrid-ci-data/github-actions/CUBRID-cubrid/commits/fb567a629cdb390fff920542173fa36f454c74a0/providers/github-actions/runs/36570256001/attempts/1/test_shell/failures/shell_37_elderberry_cbrd_23842_cdc_bug_cbrd_27075_cases_cbrd_27075_sh-f42063033e/message.txt`

```text

EnvIdentify: EnvId=local[parallel-49]
Hostname: cubrid-arc-586zc-runner-2l56v-workflow
cbrd_27075-1 : NOK
=== page size 4K (payload 20480 bytes) ===
config 4K: FINAL_SEQ=2000 CORRUPTION=0 DRIVER[FIND_OK=30 FIND_NOTFOUND=0 FIND_ERR=0 EXTRACT_ERR=4 TOTAL_ITEMS=295]
=== page size 8K (payload 40960 bytes) ===
config 8K: FINAL_SEQ=2000 CORRUPTION=0 DRIVER[FIND_OK=30 FIND_NOTFOUND=0 FIND_ERR=0 EXTRACT_ERR=4 TOTAL_ITEMS=304]
=== page size 16K (payload 81920 bytes) ===
config 16K: FINAL_SEQ=2000 CORRUPTION=0 DRIVER[FIND_OK=30 FIND_NOTFOUND=0 FIND_ERR=0 EXTRACT_ERR=4 TOTAL_ITEMS=300]
NUM_CONFIGS=3
CONFIGS_OK=0
TOTAL_CORRUPTION=0
22:36:02----/home/cubrid-testcases-private-ex/shell/_37_elderberry/cbrd_23842_cdc/bug/cbrd_27075/cases--- time=251
```
