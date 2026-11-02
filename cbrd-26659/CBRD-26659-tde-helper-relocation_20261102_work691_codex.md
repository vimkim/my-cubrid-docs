# CBRD-26659 TDE helper 공용 이동과 AES crash 검증

작성일은 2026-11-02, Asia/Seoul이다. TC 작성자와 QA 리뷰어를 위한 Work691 결과다. 질문은 일반·heavy suite에서 WAL owner TC를 선택하지 않아도 TDE 관측 의존 파일이 남고 기존 계약을 유지하는지다. 상위 Work456과 완료된 metadata 단위 Work662에서 이어졌다.

두 suite의 helper와 AWK를 기존 `oos_common`으로 옮겼다. 실제 선별의 수정 전 누락 7개 경로를 수정 후 같은 검증기로 통과했다. Owner가 없는 선별 입력으로 원문 committed crash를 AES 설정에서 실행해 1 PASS를 확인했다. 일반·heavy TC head에 각각 게시했고, 이후 한 번 요청한 CI와 다섯 gha context는 모두 SUCCESS로 종료했다.

관련 PR은 [Engine #8128](https://github.com/CUBRID/cubrid/pull/8128), [일반 TC #4365](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4365), [heavy TC #4627](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4627)이다. 비활성 TC 복원, wrapper의 별도 sibling 의존성 수리, SQL 집계, 나머지 Work456 TODO는 이번 범위가 아니다. TC PR은 사람이 리뷰·병합한다.

## 변경과 고정 리비전

| 대상 | 변경 전 | 게시 커밋·원격 head |
| --- | --- | --- |
| Engine `vimkim/cubrid` | `e3589ae42d42b04eb020e1ae43e165b01d31b12a` | 변경 없음. `CBRD-26659-oos-testcases-handover`, base `feature/oos-merge` |
| 일반 `CUBRID/cubrid-testcases-private-ex` | `41eae6a9c30f98434521c44476aa27e768e3332b` | `01df2600ac75180812451462b5c044cfa56b732a`, `tc/pr-8128` |
| Heavy `vimkim/cubrid-testcases-private-ex` | `81e60724a30431282c08ae1f677bf8cefb3d95d7` | `d5247632b19a0905eefadee6ce39a8e1ab667c9f`, `tc/pr-8128` |
| Public `CUBRID/cubrid-testcases` | `b038c424b6a8d078671132e2369040493a5fc1f6` | 변경 없음 |
| CI 선별 소스 `CUBRID/cubridci` | `155c265eb6e3deef49ce828e6f2b5846d3a9abf5` | `docker/ci/docker-entrypoint.sh`, SHA-256 `55965b9c36c67c4f4330b7954202ea292eb617b9139f9bfa46a6f27d283557d2` |

일반 경로는 `shell/_40_guava`, heavy 경로는 `shell_heavy/_40_guava`를 기준으로 한다. `cbrd_26659_tde_wal/cases`의 `tde_observe.sh`·`tde_headers.awk`를 각 `oos_common`으로 함께 옮겼다. [Helper](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/01df2600ac75180812451462b5c044cfa56b732a/shell/_40_guava/oos_common/tde_observe.sh#L6)의 JSON source 한 곳만 `"$here/oos_json.sh"`로 바꿨다. [AWK](https://github.com/CUBRID/cubrid-testcases-private-ex/blob/01df2600ac75180812451462b5c044cfa56b732a/shell/_40_guava/oos_common/tde_headers.awk)는 bytes·mode를 유지했다. Helper·AWK·JSON은 두 suite에서 각각 같다.

각 suite의 `oos_crash.sh` 호출 2곳과 WAL 호출 5곳, 일반 비활성 `tde_storage` 호출 1곳을 바꿨다. Crash는 helper 자신의 위치에 따라 `"$here/tde_observe.sh"`를 부른다. WAL·storage는 testcase의 `cases`에서 `../../oos_common/tde_observe.sh`를 부른다. CLI, stdout, 종료값, assertion, 원래 mode와 비활성 위치를 유지했다. 일반 활성 31개·heavy 38개 선택도 유지했다.

Heavy의 과거 일반 `shell` tree와 최초 이관 `pr8128-transfer.tsv`는 그대로다. 기존 공용 README에 2026-11-02 이동 위치만 덧붙였다. 일반 공용 README는 원래 없어서 새로 만들지 않았다. Engine의 사용자 `cubrid-cci`·`cubrid-jdbc` 변경도 보존했다.

## 계약과 실제 선별 증거

`identity`는 저장된 class·heap·OOS identity를 비교한다. `wal`은 지정한 RVOOS INSERT·DELETE의 TDE flag 진단 수를 검사한다. `parameters`는 유효 key 경로·AES·진단·compression 값을 검사한다. `owned`는 전체 file header와 저장된 identity를 결합해 heap·OOS 소유자와 algorithm을 검사한다. 모든 명령은 JSON helper를 source하며 `owned`는 AWK도 필요하다. 상세 호출 근거와 wrapper 경계는 [이전 의존성 감사](CBRD-26659-helper-dependency-audit_20261031_6334dc6_codex.md)를 따른다.

[검증기](tools/verify-tde-relocation.py)는 suite·시나리오·입력 fixture 표를 사용한다. 고정 baseline blob과 현재 파일의 허용된 경로 치환·mode를 대조한다. 실제 호출 인자를 읽어 testcase 작업 경로에서 해석하고, CI의 실제 `keep case`를 별도 복사본에서 실행한다. 원래 비활성 진입점은 scratch에만 투영한다. 각 명령의 argv·cwd·종료값·stdout·stderr, 투영 provenance와 선별 전후 inventory를 남긴다.

| 대조 | 관측 |
| --- | --- |
| 수정 전 최종 gate | 실제 선별 18회 완료. Owner 제외 7개 경로에서 helper·AWK 삭제와 parser exit 127. 이에 대응하는 21개 check 실패로 전체 exit 1 |
| 수정 후 같은 gate | 실제 선별 18회 완료. 요구된 파일·선택 진입점의 bytes·mode 보존과 parser 성공. 전체 exit 0 |
| 독립 parser 기대값 | fixture 52개를 두 suite에 적용한 104개 old/current 쌍, 총 208 helper 호출. 네 명령의 독립 기대값과 이전·새 출력·종료값 일치 |
| 전이 의존성 제거 대조 | 두 suite에서 AWK 또는 JSON을 제거한 4개 fixture 모두 실패 |
| 원문 native AES 대표 | Owner 제외 후 입력 35개. Committed crash 1 PASS·0 FAIL·0 SKIP, assertion 11개 |

선별 18회는 owner 제외 7회, owner 포함 7회, WAL owner 단독 2회, wrapper-only 음성 대조 2회다. Wrapper의 TDE helper를 보는 두 주 대조에서는 sibling crash 진입점도 명시적으로 선택했다. Wrapper만 선택한 대조에서는 sibling이 계속 삭제된다. 따라서 helper 이동이 wrapper의 독립 실행까지 해결했다는 뜻은 아니다.

Parser 양성 입력은 NONE·AES header, 동일 identity, 두 WAL index의 정확한 수와 최소 초과 수, quoted key path와 일치하는 중복 parameter를 포함한다. 거부 입력은 변경·누락 identity, 복수 JSON 문서, 잘못된 algorithm·class·HFID·table, 중복 VFID, 누락·중복·잘못된 header, 빈 진단과 ERROR·FATAL·UNKNOWN-CLASS, 잘못된 WAL 기대와 parameter를 포함한다. 기대값은 관측 출력에서 만들지 않았다. Stderr는 helper의 알려진 두 위치 prefix만 정규화하고 원문도 남겼다.

최종 수정 전·후 gate의 검증기 SHA-256은 `8964f3b6a45d3fc3ac22e1cb9bafce509a0db2140f7d6800fc2d1a4b28f393a2`로 같다. 도구 개발 중 bare helper 이름을 못 읽은 초안과, 이동한 storage를 중복 baseline check가 잘못 거부한 selfcheck도 별도 보존했다. 전자는 matcher를 고쳤고 후자는 정확한 경로 치환 check를 유지한 채 중복 check를 제거했다. 누락 파일 생존 기대나 parser 기대값을 완화하지 않았다. 이 횟수는 DB testcase PASS 수가 아니다.

문서 저장소 루트에서 새 Git 밖 산출물 경로를 만들어 재실행한다.

```bash
mkdir -p /home/vimkim/temp/work691-replay
python3 cbrd-26659/tools/verify-tde-relocation.py \
  --regular /home/vimkim/gh/cubrid-testcases-private-ex/tc-pr-8128 \
  --heavy /home/vimkim/gh/cubrid-testcases-private-ex/CBRD-26659-oos-shell-heavy \
  --ci-source /home/vimkim/gh/cubrid-dockerfiles-cubridci \
  --artifacts /home/vimkim/temp/work691-replay
```

## 원문 committed AES crash의 native 결과

대표는 heavy의 `cbrd_26659_crash_committed/cases/cbrd_26659_crash_committed.sh`다. 원문 SHA-256은 `2287d3d4ce0247e8c44e0a292f9000c2f73ca274b637997b4d5e536074a8a12d`, mode는 `0755`다. `OOS_CRASH_ENCRYPTION=AES`를 명시했다. Owner 제외의 실제 선별 결과 35개 전부를 corpus에 복사했고 WAL owner의 `cases`는 없다. 원문 진입점·assertion을 고치지 않았다. [Native 증거 검증기](tools/verify-tde-native.py)는 복사본과 최종 heavy 커밋 `d5247632b`의 입력 35개 bytes·mode까지 대조한다.

기본 host debug 설치는 source `e3589ae`와 installed `1ef86a7` 불일치로 실행 전 거부했다. 기존 보고서의 matching optdebug producer `/home/vimkim/temp/oos-tc-runtime-20261028/engine/CUBRID`를 새 물리 경로 `/home/vimkim/temp/w691-kkjcw8fd/n01/cubrid`에 복사했다. Preflight에서 source/install 일치를 확인했고 mismatch 예외는 쓰지 않았다. 이전 runtime 기준과 producer·실행 복사본의 바이너리·library 6개 hash를 대조했다. 이는 관측한 설치 identity·bytes의 대응이며 전체 build provenance 인증은 아니다.

Testkit SHA-256은 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`다. `go version -m`도 보존했다. CTP는 기존 로컬 asset checkout의 별도 복사본이며 legacy runner는 호출하지 않았다. 수정된 도구 source와 binary의 완전한 대응은 주장하지 않는다.

이번 native 시도는 `n01` 한 번이다. CUBRID·CTP·HOME·tmp·cache·slot을 전용 경로로 분리했다. 복사된 DB registry와 CTP 결과는 이름을 바꿔 보존하고 새 빈 registry·결과 경로를 썼다. 짧은 실제 install 경로는 [직전 준비 교훈](CBRD-26659-policy-metadata-relocation_20261102_41eae6a9c_codex.md#준비-환경-오류의-구분)을 적용한 것이다. 과거 실패 registry나 실행 장소를 재사용하지 않았다.

`TESTKIT_NATIVE=shell`, `TESTKIT_CONTAIN=1`, slot 1개, `scenario_disk=on`, retry 0, continue·answer update 없음, case patch 없음이다. Testcase와 전체 명령은 120초, 전체 명령의 TERM 뒤 종료 유예는 10초다. 원문 내부 timeout은 그대로다. 전체 명령은 약 37.55초에 exit 0으로 끝났고 focused artifact 검증도 exit 0이다. 이 시간은 제한 안의 종료 관측이며 성능 비교 수치가 아니다.

실제 journal은 다음을 증명한다.

- Baseline·recovered의 `tde-owned` command receipt가 각각 exit 0이며 argv가 이동한 `oos_common/tde_observe.sh`와 `AES`를 가리킨다.
- 두 `encrypted_file_ack`의 algorithm이 AES다. Retained header·joined proof는 heap·OOS의 table·class·VFID·HFID와 AES를 일치시킨다.
- Owned server·master의 SIGKILL receipt, recovery readiness, OOS REDO 4개, 예상 row id `1,2,4,5`의 recovered values acknowledgement, checkdb exit 0과 committed `scenario_pass`가 있다.
- 마지막 process cleanup은 owned child·utility group 종료를 확인한다. Native assertion 11개와 status·dispatch·finish·XML이 정확한 1 PASS를 지지한다.

정리 후 1초 간격의 read-only scan 두 번에서 이 실행에 속한 process·관측된 전용 namespace holder, 실행 경로 아래 host mount·UNIX socket 잔류가 없다. 두 scan 모두 읽지 못한 process 5개를 기록했다. 별도 cleanup signal은 보내지 않았다. Host 전체 IPC 객체의 부재를 인증하는 검사는 아니다.

다음 명령은 보존된 산출물을 읽으며 새 native 실행을 시작하지 않는다.

```bash
python3 cbrd-26659/tools/verify-tde-native.py \
  --attempt /home/vimkim/temp/w691-kkjcw8fd/n01 \
  --tc /home/vimkim/gh/cubrid-testcases-private-ex/CBRD-26659-oos-shell-heavy \
  --commit d5247632b19a0905eefadee6ce39a8e1ab667c9f
```

이 결과는 committed AES 대표와 이동한 `owned` 경로의 근거다. Undo crash, 일반 비활성 TC, 네 명령 전체의 native 실행, ciphertext 검사, HA, whole-corpus shell equivalence나 Work456 전체 완료로 확대하지 않는다.

## TC 게시와 단일 CI

두 TC 커밋은 각 PR의 실제 head repository와 `headRefName`을 다시 조회해 게시했다. 일반 push 직후 PR head 응답이 아직 이전 값을 보여 원격 branch ref와 이후 PR 응답으로 성공을 재확인했다. 중복 push는 하지 않았다. Publication receipt 작성 전의 CI launcher 준비 오류도 남겼으며, 이 오류는 command 게시 전에 끝났다.

Feature testcase baseline 검사는 게시 전·요청 직전에 통과했다. 기존 CI는 종료 상태였고 새 `/run`이 없음을 재확인했다. 같은 Engine head에서 새 TC 게시를 검증하는 한 번의 [요청](https://github.com/CUBRID/cubrid/pull/8128#issuecomment-6575172511)을 게시했다. 다섯 gha context 모두 [CI 41431239377](https://github.com/CUBRID/cubrid/actions/runs/41431239377)를 가리키는 pickup을 확인했다.

Plan job 원문 로그에서 Engine `e3589ae42d42b04eb020e1ae43e165b01d31b12a`, public `b038c424b6a8d078671132e2369040493a5fc1f6`, private `01df2600ac75180812451462b5c044cfa56b732a` checkout을 확인했다. Workflow run 자체의 `head_sha`를 tested Engine commit으로 대신 쓰지 않았다.

CI는 SUCCESS로 종료했다. GitHub의 최종 `updated_at`은 2026-11-02 21:42:54 KST이며, 21:43:41 KST 관측에서 job 72개가 모두 종료돼 성공 71개·skip 1개였다. 남은 60개 shard가 대기하다가 20:56 KST에 첫 실행을 관측했고 21:08 KST에는 대기가 해소됐다. 이는 실행·대기 상태의 관측이며 대기 원인을 확정한 결과가 아니다.

| 최종 context | 상태 |
| --- | --- |
| `gha-ci: build (release)` | SUCCESS |
| `gha-ci: build (debug)` | SUCCESS |
| `gha-ci: test_shell` | SUCCESS |
| `gha-ci: test_sql` | SUCCESS |
| `gha-ci: test_medium` | SUCCESS |

다섯 context 모두 같은 run을 가리킨다. `gh pr checks --required`는 exit 1과 `no required checks reported`를 반환했다. TC Merge Gate context는 최종 check 목록에 없다. 자동 TC PR #4365·#3688은 모두 OPEN이고, heavy #4627도 OPEN draft다. 따라서 CI SUCCESS를 TC Merge Gate PASS나 TC 병합으로 해석하지 않는다. Agent는 TC PR을 merge·close하거나 branch를 삭제하지 않았다.

일반 CI가 heavy fork의 새 TDE 경로를 실행했다는 근거로 사용하지 않는다. 그 경로의 native 근거는 앞의 별도 AES 대표다. SQL 전체 자료 정합성의 기존 미인증 상태도 그대로다. 종료 뒤 Engine `e3589ae`와 사용자 CCI·JDBC dirt, public `b038c424`, 일반·heavy 게시 커밋과 clean 상태를 재확인했다. 추가 TC/source 수정·push·CI 재실행은 하지 않았다.

## 보존 자료와 남은 범위

Git 밖 evidence root는 `/home/vimkim/temp/w691-kkjcw8fd`다. `decisions.tsv`는 이번 실행의 append-only 기록이다. `before.json`은 최종 수정 전 result 사본이며 원본은 `tde-relocation-4fxe8nt3/result.json`이다. 실제 수정 후 결과는 `tde-relocation-ahavw6ur/result.json`이다. `native-proof.json`, `n01` 전체, `tc-commits.json`, `publication.json`, `ci-trigger`와 `ci-status`를 보존한다. 초기 도구 시도와 별도 복사본 selfcheck도 각 `tde-relocation-*` 아래에 남겼다.

Git에는 이 보고서·체크리스트·색인과 검증 도구 두 개만 남긴다. 첫 도구는 parser 계약·실제 선별을, 둘째 도구는 retained AES artifact·최종 TC commit 대응을 재검토하는 데 필요하다. Raw log·inventory·실험 launcher·설계 후보·transcript는 Git 밖에 둔다.

`gpt-6-astra` 독립 검토는 TC diff 범위, parser·선별·native·게시 증거를 확인했다. Retained header를 다시 파싱해 두 AES proof와 일치를 확인했고, 선별 후 inventory도 대조했다. 도구 개발과 준비 오류의 trail 누락은 append-only 행으로 보완했다. 이 검토 시점에는 CI 종료와 최종 문서 커밋은 미완료였다. 노출된 모델이 모두 GPT 계열이어서 다른 계열 간 검토는 수행하지 못했다.

[전체 체크리스트](CBRD-26659-todo-checklist_20261029_codex.md)의 다른 native 검증·재활성화, 종료 지연, SQL 집계 정합성, heavy·HA 운영·리뷰·실제 TC 병합은 계속 남는다. 이 단위의 종료 보고 뒤 추가 TC/source 수정·push·CI 재실행은 사람의 다음 지시를 기다린다. 문서 main 통합도 별도 승인 대상이다.
