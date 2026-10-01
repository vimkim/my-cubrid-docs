# Evidence excerpts for PR 7990

These are selected lines from retained CI evidence. Line numbers refer to the original local `message.txt` or GitHub job-log member. Omitted lines include unrelated setup and environment data. The full exact-commit bundle and all failure paths are listed in [validation.json](validation.json). [Main report](../ci_analysis_report_fb567a6_codex.md).

## cbrd_26349 failure output

```text
4: cbrd_26349-1 : OK
5: cbrd_26349-2 : NOK
6: In the command from line 1,
7: ERROR: Failed to get column information for table [tbl] on remote [srv_wrong_pwd]
8: Incorrect or missing password.[CAS INFO-10.233.111.100:13091,0,0].
9: In the command from line 1,
10: ERROR: Failed to get column information for table [tbl] on remote [srv_wrong_pwd]
11: Incorrect or missing password.[CAS INFO-10.233.111.100:13091,0,0].
12: In the command from line 1,
13: ERROR: Failed to get column information for table [tbl] on remote [srv_wrong_pwd]
14: Incorrect or missing password.[CAS INFO-10.233.111.100:13091,0,0].
15: cbrd_26349-3 : NOK
16: In the command from line 1,
17: ERROR: Failed to get column information for table [tbl] on remote [srv]
18: Incorrect or missing password.[CAS INFO-10.233.111.100:13091,0,0].
19: === <Result of SELECT Command in Line 1> ===
20:               count(*)
21: ======================
22:                    100
23: === <Result of SELECT Command in Line 1> ===
24:               count(*)
25: ======================
26:                    100
27: cbrd_26349-4 : OK
28: 22:32:00----/home/cubrid-testcases-private-ex/shell/_40_guava/cbrd_26349/cases--- time=19
```

Selected trace lines:

```text
259: + error_cnt2=3
261: + csql_res2=3
263: + wrong_err_cnt2=3
301: + error_cnt3=1
303: + csql_res3=3
305: + wrong_err_cnt3=1
307: + server_err_cnt3=0
```

Original message SHA256: `9b0bf5a56f8630af5dd85db6223ca15a8286f07562f87756f7024b9221a5b55b`.

## hide_cubrid_replay failure output

```text
4: hide_cubrid_replay-1 : OK
5: hide_cubrid_replay-2 : OK
6: hide_cubrid_replay-3 : OK
7: hide_cubrid_replay-4 : OK
8: hide_cubrid_replay-5 : OK
9: hide_cubrid_replay-6 : OK
10: hide_cubrid_replay-7 : NOK
11: diff qa9.answer result.txt failed
12: ******							      <
13: hide_cubrid_replay-8 : OK
14: hide_cubrid_replay-9 : OK
15: hide_cubrid_replay-10 : OK
16: hide_cubrid_replay-11 : OK
17: 22:18:41----/home/cubrid-testcases-private-ex/shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases--- time=60
18: ============================= CONSOLE OUTPUT =============================
```

Selected trace lines:

```text
11: diff qa9.answer result.txt failed
120: ERROR: Method "add_user" not found.
125: ERROR: Method "add_user" not found.
130: ERROR: Method "add_user" not found.
135: ERROR: Method "add_user" not found.
140: ERROR: Method "add_user" not found.
146: wu1 is not defined.
176: User qa9 is not in the database.
305: cci connect error. url [cci:cubrid:localhost:13091:18226:::]
319: cci connect error. url [cci:cubrid:localhost:13091:18226:::]
327: start to compare files: diff qa9.answer result.txt
328: 1d0
329: < ******
336: cci connect error. url [cci:cubrid:localhost:13091:18226:::]
372: cci connect error. url [cci:cubrid:localhost:13091:18226:::]
386: cci connect error. url [cci:cubrid:localhost:13091:18226:::]
```

Original message SHA256: `978323d9c9608d971916d53eb745875f7f349b44622bd17b617bf589de67ca54`.

## bug_bts_15156 failure output

```text
4: bug_bts_15156-1 : NOK
5: 22:15:15----/home/cubrid-testcases-private-ex/shell/_06_issues/_15_1h/bug_bts_15156/cases--- time=228
6: ============================= CONSOLE OUTPUT =============================
```

Selected trace lines:

```text
147: + kill -9 27617
170: + master=1
179: + '[' 0 -eq 1 ']'
187: + '[' 0 -eq 1 ']'
195: + '[' 0 -eq 1 ']'
203: + '[' 0 -eq 1 ']'
211: + '[' 0 -eq 1 ']'
219: + '[' 0 -eq 1 ']'
227: + '[' 0 -eq 1 ']'
235: + '[' 0 -eq 1 ']'
243: + '[' 0 -eq 1 ']'
251: + '[' 0 -eq 1 ']'
259: + '[' 0 -eq 1 ']'
267: + '[' 0 -eq 1 ']'
275: + '[' 0 -eq 1 ']'
283: + '[' 0 -eq 1 ']'
291: + '[' 0 -eq 1 ']'
299: + '[' 0 -eq 1 ']'
307: + '[' 0 -eq 1 ']'
315: + '[' 0 -eq 1 ']'
323: + '[' 0 -eq 1 ']'
331: + '[' 0 -eq 1 ']'
339: + '[' 0 -eq 1 ']'
345: ++ grep 'cubrid master start: success'
352: + '[' 0 -eq 1 ']'
353: + write_nok
360: + internal_err=0
```

Original message SHA256: `922bf77d9a1390b8215fdebbf00d21918ae3b9d7ef9b0f00c469cb70b69f86c3`.

Final assertion trace:

```text
343: + '[' Linux == Windows_NT ']'
344: ++ cat service.log
345: ++ grep 'cubrid master start: success'
346: ++ wc -l
347: + '[' 1 -ge 1 ']'
348: + '[' 1 -eq 1 ']'
349: ++ cat server.log
350: ++ grep 'cubrid server stop: success'
351: ++ wc -l
352: + '[' 0 -eq 1 ']'
353: + write_nok
```

## Retry setting evidence

Cache `run-log-36570256001-1790685926.zip`, member `60_shard shell 17.txt`, member SHA256 `bd572f680ee1d8484a82637560ecbd998343e3c9db6945fd91e3394c599dcaaa`:

```text
839: 2026-09-29T12:58:25.2143879Z ctp SHA   : 4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb
1073: 2026-09-29T12:58:27.4247051Z testcase_retry_num=0
1124: 2026-09-29T12:58:27.4990073Z testcase_retry_num=0
```

Cache `run-log-36570256001-1790685926.zip`, member `17_shard shell 35.txt`, member SHA256 `2d04eab8a3f430913a49518934610d88f9fd8d22ba7f21115bb5b94c2e7b0493`:

```text
839: 2026-09-29T12:59:44.5318526Z ctp SHA   : 4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb
1073: 2026-09-29T12:59:46.8095176Z testcase_retry_num=0
1124: 2026-09-29T12:59:46.8823163Z testcase_retry_num=0
```

Cache `run-log-36570256001-1790685926.zip`, member `8_shard shell 46.txt`, member SHA256 `4eff74c5ed5434c92059177e107e1df6535259638647aeee085ec1df702f00c9`:

```text
839: 2026-09-29T13:10:13.3256300Z ctp SHA   : 4d0043a7b149b3fc5d3ccb2e08c98cf8d77b34fb
1073: 2026-09-29T13:10:15.7570415Z testcase_retry_num=0
1124: 2026-09-29T13:10:15.8287697Z testcase_retry_num=0
```

Cache `run-log-36104247286-1790318674.zip`, member `4_shard shell 17.txt`, member SHA256 `4cef7dc1e0a92cf1610bfd2262a587b612881fd9603011f0cd88cb4eae47810a`:

```text
839: 2026-09-25T06:49:01.8705848Z ctp SHA   : db9074728040c29532b4feb5da4d9640fb09f9fc
1073: 2026-09-25T06:49:03.9762678Z testcase_retry_num=1
1124: 2026-09-25T06:49:04.0442097Z testcase_retry_num=1
```

## Earlier replay failures

These historical cached records are not part of the validated current-run bundle and are not matched engine comparisons. They establish earlier terminal NOK records under the retry setting then in use; they do not identify the precise historical assertion.

Cache `run-log-35544984896-1789947194.zip`, member `24_shard shell 06.txt`, SHA256 `11c7f934e211c4852d1de1cfa5255a009fafa57874f1d261302e54efe072ea75`:

```text
1094: 2026-09-20T23:54:27.3526772Z testcase_retry_num=1
1145: 2026-09-20T23:54:27.4330624Z testcase_retry_num=1
1349: 2026-09-21T00:22:53.9640451Z [TESTCASE] cubrid-testcases-private-ex/shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh EnvId=local [NOK], TRY->1
1356: 2026-09-21T00:22:54.5032608Z Total Fail Case:1
```

Cache `run-log-35827226490-1790145148.zip`, member `31_shard shell 01.txt`, SHA256 `05d8d0d8856e2fa52a52b39016c6f0de5e8a01c3a0f5c64a3c4b480d26a7a603`:

```text
1073: 2026-09-23T07:18:04.5345039Z testcase_retry_num=1
1124: 2026-09-23T07:18:04.6085355Z testcase_retry_num=1
1327: 2026-09-23T07:45:24.8479665Z [TESTCASE] cubrid-testcases-private-ex/shell/_06_issues/_17_1h/cbrd_20759/hide_cubrid_replay/cases/hide_cubrid_replay.sh EnvId=local [NOK], TRY->1
1334: 2026-09-23T07:45:25.5276103Z Total Fail Case:1
```
