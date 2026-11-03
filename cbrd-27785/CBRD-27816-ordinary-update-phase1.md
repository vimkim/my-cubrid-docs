# CBRD-27816 1단계 보고서

갱신: 2026-11-03 20:13 KST. 1단계(재현과 원인 분리) 측정을 마쳤다. 검토에서 나온 정정과 L1, L1b, h3 결과, 18:51 사용자 결정을 반영했다. 할 일과 결정 사항은 이 파일에서 관리한다.

관련 이슈: [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816), [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785). 관련 PR: [#8299](https://github.com/CUBRID/cubrid/pull/8299). 이 보고서는 2026-11-03에 로컬 산출물 디렉터리 `/mnt/nvme/data-5/tmp/CBRD-27816-20261103/phase1-report.md`에서 옮겨 왔다. 본문의 상대 경로(`harness/`, `base|cand/...`, `decisions.tsv` 등)는 모두 그 디렉터리 기준이다.

## 목표

- PR #8299 head `4c3c8d791`의 일반 테이블 UPDATE가 develop `4781495`보다 서버 user instructions를 더 쓰는 원인을 실행 근거로 가린다.
- 가끔 늦게 나타나는 높은 표본(+5.0158%, +3.84%)의 출처를 가린다.
- 1단계는 재현과 원인 분리만 한다. 엔진 코드는 바꾸지 않는다.
- 명세는 `work-tracker show 571`의 Description이다.

## 1단계 결론

1. **정상 상태 차이는 +86.8M(+1.34%)다.** 판정 구간(csql 하나), c1, 한쪽당 유지 표본 36개 기준이다. 차이는 transaction worker 하나에 있다(+86.2M). log-flush는 같다.
2. **worker 차이는 세 경로의 증가에서 줄어든 몫을 뺀 것이다.** 셋은 서로 겹치지 않는다(`--under`로 확인).
   - A. record 복사 +54.0M. **20:13 정정: 실제 증가가 아니다.** 기준 build는 `spage_get_record`를 tail call(`jmp`)로 불러서 그 복사가 profile에서 `heap_get_last_version` 바로 아래에 잡혔다. 후보는 일반 `call`이다. `heap_get_last_version` 전체로 보면 후보가 −14.2M다. 아래 "2단계 첫 일" 절
   - B. OOS 열이 없는 행에서도 도는 OOS 처리 약 +61M
   - C. `heap_update_logical` 안의 증가 +51.2M

   셋의 합은 약 +166M다. PR이 줄인 몫(record 만들기 −44.7M, 속성 읽기 −21.8M, page fix −29.0M 등)이 이를 상쇄한다. profile 표본 합계 기준 순증가는 +79.2M이고, plain 값은 +86.2M다. 줄어든 쪽 합계는 경로가 겹쳐 정확히 닫지 못했다.
3. **늦은 spike의 크기는 계수 구간과 비동기 vacuum의 경쟁으로 설명된다.** UPDATE 하나가 남기는 vacuum은 기준 약 390M, 후보 약 425M다. COMMIT 직후 시작한 vacuum의 일부나 전부가 csql 종료 전에 계수 구간에 들어오면 표본이 커진다. 관측한 spike는 모두 이 전체량보다 작았다. 이번 세션에서는 17~273M였고, 10-28에는 +305M와 +361M, 10-29 +3.84% 표본은 +133M였다.
4. **"늦은" spike는 바쁜 호스트 아래 오래 떠 있는 서버에서 재현됐다.** 기준 r503에서 호스트 전체가 100%가 된 뒤 12개 표본 모두에 vacuum 135~316M가 들어왔다. 10-28과 같은 모양이다. 그러나 정확한 시점 메커니즘과 빈도는 확인하지 못했다. 호스트가 100%였던 다른 표본에서는 0~66M였고, client만 느리게 하는 조작(h3)은 csql을 느리게 하지 못했다. vacuum 시작과 csql 종료 사이 시간도 재지 않았다.
5. **"vacuum-master spike"는 별도 원인이 아니다.** 구간 중에 새로 생긴 vacuum worker의 계수를 perf가 부모 thread(vacuum-master)에 합친 것이다. 그 표본에서 vacuum-master thread 자신의 `/proc` CPU tick은 1개(약 10ms)였다. 그런데 perf 줄에는 204~221M instructions와 task-clock 69~76ms가 잡혔다.
6. **후보 vacuum은 UPDATE 하나당 +34.6M(+8.9%) 더 든다.** 대부분 로그 record 처리(`vacuum_process_log_record`, +21.7M)에 있다. PR이 `RVHF_UPDATE_NOTIFY_VACUUM` record에서도 undo를 풀고 OOS를 검사하기 때문이다(`vacuum.c:4276`). 이 비용은 대부분 판정 구간 밖에서 쓰인다.
7. **기각한 가설.**
   - log archive 생성
   - 호스트가 느린 것 자체 (h1, h2에서 재현되지 않음)
   - 후보 vacuum이 기준의 2배라는 가설
   - PR의 중단 job 재시도(`force_data_update (true)`)
   - 크기 기준 checkpoint. 오래 떠 있는 서버(L1, L1b)에서 checkpoint가 구간에 들어와도 spike는 없었다(약 3M). 다만 checkpoint 뒤 서버가 21~22초 동안 idle이 되지 않아, `ordinary.py`의 10초 마감에 걸릴 수 있다(L1 후보 실패).
8. **+2% 판정.** 판정 구간의 정상 상태 값(+1.34%)은 +2% 안이다. 그러나 명세의 지표는 spike를 포함하고, vacuum이 다 들어오면 +6.5%까지 갈 수 있다. 그래서 +2% 기준은 여전히 미충족이다. vacuum을 늘 포함하는 꼬리 지표로는 +121~125M(+1.76~1.82%)다(t1, 진단 전용).

## 할 일

- [x] 후보 release 빌드. `UNIT_TEST_*` 모두 OFF, 기준과 compile flag 일치
- [x] 2G 데이터·1G 로그 DB 두 개 생성, 서버를 띄우기 전 사본 보존
- [x] thread별 계수 harness(`harness/threads.py`), smoke run 양쪽
- [x] c1: ABBA 8라운드. 정상 상태 차이와 spike 확인
- [x] h1: 서버 CPU 경합. spike 재현 안 됨
- [x] h2: sibling 메모리 hog. IPC 0.87~0.96, spike 재현 안 됨
- [x] t1: 꼬리 3초 계수. vacuum 양 측정
- [x] p1: period 1M profile. throttle로 표본 약 40% 손실, 쓰지 않음
- [x] p1b: period 3M profile, worker 경로별 분해
- [x] p3: 꼬리 3초 profile, vacuum 경로별 분해
- [x] spike B 재분류
- [x] 다른 모델 검토, 정정 반영 (아래 "검토에서 나온 주의 사항")
- [x] L1: 서버 한 번에 UPDATE 20개 (r500). 기준은 완료. checkpoint가 구간에 들어와도 spike 없음. 후보는 UPDATE 10개 뒤 idle 대기 실패
- [x] L1b: 후보·기준 1 block씩 (r503). checkpoint 대기는 양쪽 21~22초. 바쁜 호스트 아래 기준에서 늦은 spike 12번 연속 재현
- [x] h3: client CPU 경합 (r600). 조작이 약해 가설을 가르지 못함. 후보 block은 harness 오류로 멈춤(파서 고침)
- [ ] 명세 항목 중 하지 않은 것. 같은 표를 연속으로 UPDATE하는 측정. `ordinary.py`가 지원하지 않아 하지 않았다
- [x] (사용자 결정) 2단계 코드 변경 여부. 18:51 1-가(A, B를 고치고 C는 더 나눈다)
- [x] (사용자 결정) 판정 지표에 vacuum 비용을 넣을지. 18:51 2-가(넣지 않고 별도 줄로 보고), 2-2 `ordinary.py` idle 마감은 늘린다
- [x] (사용자 결정) DB 정리. 18:51 3-가(그대로 둔다). 산출물은 1단계 중간에 57G(DB 각 26G, pristine 6.1G)였고, 20시에는 약 27G(`db-base` 11G, `db-cand` 9.8G, `pristine` 6.1G)다. 줄어든 것은 서버 자신이 log archive를 지웠기 때문이다. 각 DB의 `*_lginf`에 `REMOVE` 기록이 두 번씩 있다(기준 17:32:43, 17:44:34, 후보 17:39:20, 17:40:28). 이유는 "Number of active log archives has been exceeded the max desired number"다. 설정은 `log_max_archives=0`이다. 기준의 두 기록은 L1 끝(r500, 17:32:56 종료)과 L1b(r503) 중이고, 후보의 두 기록은 L1b(r503, 17:41:07 종료) 중이다
- [x] (사용자 결정 뒤) my-cubrid-docs로 옮기기. 2026-11-03 20:05, `cbrd-27785/` (4-가)

## 사용자 결정 기록

2026-11-03 16:47 사용자가 다섯 항목 모두 권장안을 골랐다.

- 판정은 명세의 계수 구간 그대로 한다. 꼬리 구간 지표는 진단용으로만 낸다.
- vacuum 비용은 t1 뒤에 정한다.
- 코드 변경은 p1 뒤에 묻는다.
- 1단계에서는 quiet 측정을 하지 않는다.
- 보고서는 1단계 뒤에 옮길지 정한다.

2026-11-03 18:51 사용자가 1단계 결정 다섯 항목에 답했다. 별도 세션이 쉬운 설명 문서(`/mnt/nvme/data-5/tmp/CBRD-27816-20261103/decisions-explained.md`)를 보이고 질문 창으로 받았다. 답만 모은 파일은 `/mnt/nvme/data-5/tmp/CBRD-27816-20261103/decision-answers.md`다.

- 결정 1(2단계 코드 변경): 1-가. A와 B를 고치고, C는 원인부터 더 나눈다. 첫 일은 OOS 규칙 확인이다.
- 결정 2(vacuum 비용과 판정): 2-가. 판정은 명세의 계수 구간 그대로 한다. vacuum 비용과 꼬리 구간 지표는 별도 줄로 보고한다. 사용자는 처음에 "뭔지 잘 모르겠어."라고 답했고, 다시 설명을 들은 뒤 골랐다.
- 결정 2-2(`ordinary.py` idle 대기 마감 10초): 늘린다. 2단계 측정 전에 local commit으로 고친다.
- 결정 3(DB 정리): 3-가. 2단계를 할지 정할 때까지 그대로 둔다.
- 결정 4(보고서 보존): 4-가. 오늘 결정을 반영한 뒤 my-cubrid-docs로 옮긴다. push는 따로 요청할 때만 한다.

## 2단계 첫 일: OOS 규칙 확인과 A·B·C 재분해 (2026-11-03 20:13)

결정 1-가에 따라 코드를 고치기 전에 OOS 규칙을 확인하고 p1b profile(r410, r411)을 다시 나눴다. 새 도구는 `harness/profile_children.py`다. 한 함수의 호출자와 직접 callee를 표본 × period로 나눈다. 결과 파일은 `p2-A-children.txt`, `p2-last-version-children.txt`, `p2-update-children.txt`, `p2-B-children.txt`, `p2-C-children.txt`다.

**OOS 규칙.** `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md`(sha256 `6300aa1f…`, 2026-10-27)를 끝까지 읽었다.

- HAS_OOS는 "record에 stub이 있을 때만 참"이다(Core Terminology). stub이 없는 record에는 Expand할 것도, 새로 넣을 OOS 값도 없다. 그래서 OOS가 없는 새 record에서 OOS 처리를 건너뛰는 것은 명세와 충돌하지 않는다.
- 단, 건너뛰는 조건은 **새** record에 stub이 없다는 것이어야 한다. 옛 record의 stub이 빠진 경우에는 commit hook의 `RVOOS_NOTIFY_VACUUM`으로 버린 chain을 알려야 한다(§3 CBRD-27230). 이 일은 finalize 경로가 아니라 update와 commit 경로에 있다.
- 명세 §5의 "PEEK mode 없음"은 OOS 계층에서 OOS 값을 읽는 방식이다. heap record를 PEEK하는 것과는 관계가 없다. 결정 세션의 "A는 PEEK가 없어 막힐 수 있다"는 메모는 이 문장을 heap record로 읽은 것이다.
- pending record의 상태 기계와 `heap_oos_begin_insert_publication`의 초기화는 명세에 없는 구현 세부다.

**A는 없다.** 기준과 후보 모두 COPY로 record를 복사한다.

| `heap_get_last_version` 직접 callee | 기준 | 후보 |
|---|---|---|
| `heap_get_record_data_when_all_ready` | 29.2 | 82.5 |
| `memmove` | 32.0 | 0 |
| `spage_get_record` + `spage_get_record_data` | 35.3 | 5.7 |
| `heap_scan_cache_allocate_area` / `assign_recdes_to_area` | 21.6 | 22.8 |
| `heap_record_replace_oos_oids` (후보는 tail call) | 0 | 8.7 |
| `heap_get_last_version` 전체 | 534.5 | 520.3 (−14.2) |

- 실행 파일로 확인했다. 기준 `libcubrid.so.11.5`의 `heap_get_record_data_when_all_ready`는 `spage_get_record`로 `jmp`한다. 후보는 `call spage_get_record` 뒤 `heap_record_replace_oos_oids`로 `jmp`한다.
- frame pointer 호출 사슬은 tail call한 함수를 빠뜨린다. 그래서 기준의 복사가 한 단계 위 함수에 잡혔다. 1단계의 `--under` 확인은 겹침만 보았고 이 이동은 보지 못했다.
- 1단계 "검토에서 나온 주의 사항"의 inlining 경고와 결정 세션 검토의 "기준도 복사한다"는 지적이 맞았다.

**B는 있지만 작고 흩어져 있다.** 행 20만 개 기준으로 행 하나당 약 300 instructions다.

| B 구성 | 후보 M | 행당 | 내용 |
|---|---|---|---|
| `heap_oos_finalize_record` | 31.5 | 157 | OOS 없는 행에서도 header 검사, `owns`, `heap_oos_begin_insert_publication`(8.3M, tdes 조회와 두 container 초기화), 길이·type 설정 |
| `heap_pending_record` 생성·소멸 | 18.8 | 94 | 새 record의 소유자. 기준의 copy area 할당·해제를 대신하므로 전부 OOS 비용은 아니다 |
| `heap_record_replace_oos_oids` | 9.7 | 16/호출 | 행마다 세 번 불린다. 정책 검사와 HAS_OOS 검사 뒤 바로 돌아온다. 거의 호출 비용이다 |
| `locator_finalize_oos_record`, `heap_recdes_contains_oos`, `heap_oos_validate_disk_record` | 8.3 | 42 | 작은 검사 |

OOS 없는 행의 finalize를 빠른 경로로 바꾸면 줄일 수 있는 양은 약 20~30M로 추정한다(추정, 측정 아님). 정상 상태 +1.34%가 약 +0.9~1.0%로 내려가는 크기다. spike는 vacuum 시점 때문이므로 바뀌지 않는다.

**C는 한 원인이 아니다.** `heap_update_logical` +51.2M는 직접 callee 25개 이상에 1~11M씩 퍼져 있다. 가장 큰 것은 자기 자신 +10.8M, `heap_log_update_physical` +9.0M, `heap_page_get_vacuum_status` +7.3M, `oid_check_cached_class_oid` +7.2M, `heap_update_physical` +7.0M다. OOS 고유 검사는 `heap_oos_validate_disk_record` +4.5M 하나다. 나머지는 code 배치와 inlining 차이로 보인다(추정). 고칠 한 곳을 가리키지 않는다.

**결론.** 정상 상태 +86.8M는 한 곳의 큰 비용이 아니라 행마다 쌓인 작은 비용의 합이다. 코드로 줄일 수 있는 것은 B의 빠른 경로 하나이고, 그 효과도 +2% 판정을 바꾸지 못한다.

## 2단계 결정 (사용자에게 묻는 것)

근거가 가리키는 코드는 다음과 같다. 1단계에서는 고치지 않았다. 수치는 UPDATE 하나당 instructions이고, p1b·p3 profile의 표본 합계 기준이다.

| 후보 | 위치 | 크기 | 판정 구간 영향 |
|---|---|---|---|
| A. 마지막 버전 읽기에서 record 복사 (20:13 정정: tail call에 의한 귀속 착시, 실제 증가 아님) | `heap_file.c:7582` `heap_get_record_data_when_all_ready`, `heap_get_last_version` 아래. 호출처는 `locator_lock_and_get_object_with_evaluation`(+28.8M), `locator_attribute_info_force`(+25.5M), `locator_update_index` → `heap_get_class_record`(+15.1M) | +54.0M | 직접 |
| B. OOS 열이 없는 행에서도 도는 OOS 처리 | `heap_oos.cpp:155` `heap_oos_finalize_record`(31.5M, `heap_oos_begin_insert_publication` 8.3M 포함), `heap_pending_record` 생성 9.3M·소멸 9.5M, `heap_record_replace_oos_oids` 9.7M | 약 +61M | 직접 |
| C. `heap_update_logical` 안의 증가 | 로그 기록 +16.3M, `logtb_find_tranid` +14.5M, `spage_update` +11.2M, `log_can_skip_undo_logging` +10.4M. 로그 양은 양쪽이 같다(UPDATE당 57.750MB 대 57.754MB) | +51.2M | 직접. 원인 코드는 특정하지 못했다 |
| D. vacuum의 undo 풀기와 OOS 검사 | `vacuum.c:4276` `vacuum_process_log_record`의 조기 반환 조건, `vacuum_oos.cpp:267` `vacuum_forward_walk_reclaim_oos` | +34.6M (vacuum) | 대부분 구간 밖, spike 때만 안 |
| E. 측정 구간 자체 | `ordinary.py`의 계수 구간이 csql 종료에서 끝난다 | spike 0~425M | 측정 방법 |

- A와 B에는 "OOS가 없는 행이면 건너뛸 수 있는가"라는 공통 질문이 있다. 1단계에서는 판단하지 않는다. `cubrid-oos-context`의 계약(공통 reader, COPY, pending owner)을 확인해야 한다.
- E와 함께 볼 harness 문제가 둘 있다. 엔진 코드는 아니다.
  - `ordinary.py`의 idle 대기 마감 10초는 checkpoint 뒤 대기(21~22초)보다 짧다. 오래 떠 있는 서버에서는 측정이 멈출 수 있다.
  - perf가 thread를 두 번 적는 경우를 파서가 거부한다. 내 harness(`harness/threads*.py`)에서는 고쳤다. `ordinary.py`는 thread별로 세지 않으므로 이 문제가 없다.
- E를 바꾸는 것은 판정 방법을 바꾸는 일이다. 명세는 background 작업을 끄거나 실패 표본을 빼는 것을 금한다. 꼬리 구간을 더하는 것은 끄는 것이 아니라 포함하는 쪽이지만, 그래도 사용자가 정할 일이다.

## 측정 점검 (benchmark-checklist)

- **제한 요인.** UPDATE 계수는 transaction worker 한 thread가 행 20만 개를 처리하는 데 든다. 행 하나에 약 30k instructions다. log-flush는 약 380M로 양쪽이 같다. 경과 시간은 판정에 쓰지 않는다.
- **조율.** 양쪽 모두 release_gcc이고 `UNIT_TEST_*`는 OFF다. compile flag가 같고 `[common]` 설정과 1GiB 로그도 같다.
- **오류.** 모든 UPDATE 뒤에 행 내용을 검증했다(`count`, `min/max id`, `a=MOD(id,100)+1`, `s=SHA2`, 길이 합계). 실패는 0이었고 block은 모두 rc=0이다.
- **재현.** ABBA로 돌렸다. c1은 한쪽당 유지 표본 36개다.
- **실제로 일했는지.** UPDATE 뒤 검증에서 모든 행이 `a+1`이었다. SELECT는 결과값을 확인했다.
- **worker 값의 두 덩어리.** worker 값은 양쪽 모두 15.9M 간격의 두 값으로 갈린다. 두 덩어리의 비율이 양쪽에서 다르면 중앙값끼리 뺀 차이가 틀어진다. 그래서 worker 차이는 같은 run 위치끼리 비교한다. c1에서는 run 1~4 모두 +86.1~86.2M였다. n이 8인 실험(h1, h2, t1)의 중앙값 차이는 이 때문에 믿기 어렵다.
- **한계.** 낮 시간 측정이고 quiet gate를 쓰지 않았다. 호스트 소음은 1초마다 기록했다(`*-host.jsonl`). profile은 throttle이 있었지만, p1b의 표본 합계(기준 6,066.2M)가 plain 값(6,081.1M)과 0.2% 차이라 손실은 작다.

## 결과

### 정상 상태 차이 (c1, 한쪽당 UPDATE 유지 표본 36개)

| 경우 | 기준 중앙값 | 후보 중앙값 | 차이 | 후보 범위 |
|---|---|---|---|---|
| UPDATE 전체 | 6,471.55M | 6,558.33M | +86.8M (+1.34%) | 6,542.20~6,831.76M |
| UPDATE transaction worker | 두 값 6,072.9 / 6,088.8 | 두 값 6,159.1 / 6,175.0 | +86.2M (같은 run 위치끼리) | |
| UPDATE log-flush | 379.74M | 379.86M | +0.1M | |
| scan | 250.87M | 248.88M | −0.79% | 248.83~248.97M |
| predicate | 531.56M | 535.97M | +0.83% | 535.89~536.05M |

- 표본은 smoke 1 block과 c1 8라운드다. block마다 warmup 1개를 버렸다.
- 앞선 판(16:45~17:25)에는 worker 차이를 +94.2M로 적었다. 이는 위에서 말한 두 덩어리 때문에 생긴 오류였다.
- 10-28에 잰 02df4d9fe의 worker 차이는 +115.9M였다. 다른 세션 값이고, 같은 오류가 있을 수 있다.

### worker 차이의 경로별 분해 (p1b, profile, 판정 수치와 별개)

- 방법은 `perf record -e instructions:u -c 3000017 --call-graph fp`, 한쪽당 유지 UPDATE 18개다.
- 값은 표본 수 × 3,000,017이다. 결과는 `p1b-transaction-inclusive-raw.txt`다.
- 값은 inclusive(자기 자신과 그 아래 호출 전부)다. 위아래 경로는 겹치므로 더하면 안 된다.

| 경로 | 기준 | 후보 | 차이 |
|---|---|---|---|
| transaction worker 표본 합계 | 6,066.2 | 6,145.4 | +79.2 |
| `qexec_execute_update` | 5,373.9 | 5,426.4 | +52.5 |
| `locator_update_force` | 2,467.5 | 2,566.7 | +99.2 |
| └ C. `heap_update_logical` | 1,032.3 | 1,083.5 | +51.2 |
| └ B. `heap_oos_finalize_record` | 0 | 31.5 | +31.5 |
| B. `heap_pending_record` 생성 / 소멸 | 0 | 9.3 / 9.5 | +18.8 |
| B. `heap_record_replace_oos_oids` | 0 | 9.7 | +9.7 |
| A. `heap_get_record_data_when_all_ready` | 29.7 | 83.7 | +54.0 |
| record 만들기 (기준 `locator_allocate_copy_area_by_attr_info`, 후보 `heap_attrinfo_prepare_record`) | 332.0 | 287.3 | −44.7 |
| 속성 읽기 `heap_attrinfo_read_dbvalues` | 229.8 | 208.0 | −21.8 |
| `pgbuf_fix_release` | 405.7 | 376.7 | −29.0 |

- record 만들기의 짝 비교는 소스로 확인했다. 같은 호출 자리를 PR이 바꿨다(기준 `locator_sr.c:7603`, 후보 `locator_sr.c:7896`).
- A의 호출처별 값(+28.8, +25.5, +15.1)은 앞선 환산 계산에서 나온 것이다. 환산 계수는 1.0025와 1.0049라서 차이가 1% 미만이다.
- A 안에서 후보는 `spage_get_record_data`와 `memmove`(+28.6M)로 record를 복사한다. 기준은 `heap_scancache::assign_recdes_to_area`(19.5M)를 쓴다.
- 질의 실행 밖(commit, 연결 처리 등)은 약 +27M이고 나누지 않았다.

### vacuum 양 (t1, 진단 전용)

계수 구간을 csql 종료 뒤 3초까지 늘렸다(`threads2.py --tail 3`). 한쪽당 유지 표본은 8개다.

| 항목 (M, 중앙값) | 기준 | 후보 | 차이 |
|---|---|---|---|
| 서버 전체 | 6,861.6 | 6,986.5 | +124.9 (+1.82%) |
| transaction worker (같은 run 위치끼리) | | | +86.2~94.2 |
| log-flush | 379.7 | 379.5 | −0.2 |
| vacuum + vacuum-master | 390.1 (383.9~403.0) | 424.7 (419.2~436.4) | +34.6 (+8.9%) |
| 나머지 daemon | 8.9 | 9.0 | +0.1 |

- 구간을 늘려 더해진 것은 vacuum과 3초 동안의 daemon 약 9M뿐이다. transaction worker와 log-flush는 그대로다.
- 서버 전체 차이 +124.9M에는 worker의 두 덩어리 영향이 섞여 있다. worker를 +86.2M로 잡으면 약 +121M(+1.76%)다.
- vacuum이 다 들어오면 기준은 +6.0%, 후보는 +6.5%가 된다.

### vacuum 차이의 경로별 분해 (p3, profile, 진단 전용)

- 방법은 `profile2.py --tail 3 --period 3000017`이고, 한쪽당 유지 UPDATE는 10개다.
- vacuum 표본은 기준 1,232개, 후보 1,317개로 적다. 항목마다 잡음이 약 ±3~6M다.
- 몫은 t1의 plain vacuum 합계(기준 389.2M, 후보 423.8M, master 약 1M 제외)로 환산했다. 결과는 `p3-vacuum-inclusive.txt`다.

| 경로 | 기준 | 후보 | 차이 |
|---|---|---|---|
| `vacuum_process_log_block` | 262.2 | 297.0 | +34.8 |
| └ `vacuum_process_log_record` | 22.7 | 44.4 | +21.7 |
| &nbsp;&nbsp;└ `vacuum_forward_walk_reclaim_oos` | 0 | 8.4 | +8.4 |
| &nbsp;&nbsp;└ `vacuum_read_log_aligned` | 7.6 | 12.2 | +4.6 |
| └ `vacuum_heap_page` | 208.2 | 216.6 | +8.4 (잡음 범위) |

- `vacuum_process_log_block`은 vacuum 비용의 약 67%만 덮는다. 나머지 1/3은 따로 보지 않았다.
- `vacuum_heap_record_insid_and_prev_version`은 후보에만 이름이 있다(99.1M). 기준에서는 inline되어 이름이 없어 비교에서 뺐다.

### spike (c1, h1, h2)

| 표본 | 초과 | IPC | 호스트 | 늘어난 thread |
|---|---|---|---|---|
| 기준 r1 update-4 | +95.1M | 2.00 | 6% | vacuum worker 10개, +109.8M |
| 기준 r6 update-4 | +28.9M | 2.02 | 6% | vacuum +27.5M |
| 기준 r4 update-3 | +16.7M | 2.02 | 5% | vacuum +16.6M |
| 기준 h1 r101 update-1 | +81.3M | 2.01 | 18% | vacuum +71.7M |
| 후보 r3 update-3 | +238.0M | 1.06 | 97% | vacuum-master 204.1M, vacuum +48.6M |
| 후보 r3 update-4 | +273.4M | 1.09 | 100% | vacuum-master 221.3M, vacuum +51.9M |
| 후보 r5 update-1 | +113.6M | 1.96 | 14% | vacuum +113.3M |
| 후보 r6 update-3 | +110.7M | 1.94 | 7% | vacuum +125.5M |
| 후보 r7 update-1 | +20.0M | 2.00 | 7% | vacuum +19.8M |
| 후보 smoke update-1 | +17.8M | 1.97 | 6% | vacuum +17.9M |

- 이 표본들에서 transaction worker와 log-flush는 평소 값이었다.
- vacuum master는 10ms마다 깨고(`vacuum_master_interval_in_msecs=10`), COMMIT 뒤 old version 정리 job을 worker에게 넘긴다.
- vacuum worker는 5초 idle이면 내려간다(`thread_worker_pool_impl.hpp:189`).
- 후보 r3의 두 표본에서는 구간 안에서 worker 9개가 새로 생겼다. 그 TID는 perf 출력에 없다. 다만 worker가 새로 생긴 표본은 h1과 h2 전부를 포함해 150개 중 70개였고, 대부분 spike가 없었다. 그래서 재분류의 결정 근거는 thread 생성이 아니다. vacuum-master 자신의 CPU tick이 1개였다는 점이다.
- 다른 표본의 vacuum-master는 대개 0.4~1.0M다. 후보 h2에서는 5.7M와 8.2M도 있었다.

### 경합 실험 (h1, h2)

| 실험 | 경합 | IPC | 경과 시간 | vacuum spike |
|---|---|---|---|---|
| h1 | 서버 CPU 16~19에 busy-loop 4개 | 1.84~2.01 | 약 2.5초 (평소 1.4초) | 기준 1번(+71.7M), 후보 0번 |
| h2 | sibling 56~59에 256MB 메모리 복사 hog 4개 | 0.87~0.96 | 약 2.9초 | 0번 |

- 두 실험 모두 한쪽당 UPDATE 10개(유지 8개)다.
- 경합을 일부러 걸어도 spike가 늘지 않았다.
- hog를 걸기 전에 그 CPU에 다른 사용자의 작업이 있는지 확인하지 않았다. h1은 사용자에게 알린 직후, 답을 받기 전에 시작했다.

### 오래 떠 있는 서버 (L1, 서버 한 번에 UPDATE 20개)

- 기준 r500은 UPDATE 20개를 모두 마쳤다.
  - u10~u11에서 크기 기준 checkpoint가 일어났다. `log-checkpoint` thread가 1.6M를 썼고, flush 계열 thread도 1.6M 늘었다.
  - 그 표본들의 합계는 평소 값이었다(6,475.2M, 6,474.8M).
  - 다음 표본의 idle 대기는 3.5초와 8.5초로 늘었다.
  - vacuum race는 u7(+119.0M), u16(+110.4M)에서 났다.
- 후보 r500은 UPDATE 10개 뒤에 멈췄다. 11번째 표본 전에 서버가 10초 안에 idle이 되지 않았다(0.25초마다 10~20ms). 기준의 checkpoint 시점과 같은 위치다. 유효한 실패로 남긴다. 캠페인은 여기서 멈췄고 r501은 돌지 않았다.
- checkpoint가 계수 구간에 들어와도 spike는 생기지 않았다(기준). 따라서 checkpoint 기각을 오래 떠 있는 서버의 기준 쪽까지 넓힌다.
- 이 실패 때문에 두 DB의 이력이 달라졌다. 후보가 UPDATE 10개(로그 약 85,000쪽)를 덜 했다.

### L1b (r503, 서버 한 번에 UPDATE 20개, idle 마감 120초, `threads3.py`)

- **checkpoint 뒤 idle 대기는 양쪽 모두 길다.** u10 직전 대기가 후보 22.3초, 기준 21.3초였다. 그동안 CPU를 쓴 thread는 양쪽이 같았다(`dwb-flush-block` 58 tick, `log-checkpoint` 13~27 tick, `dwb-file-sync` 8 tick). 따라서 L1 후보 실패는 후보만의 문제가 아니다. `ordinary.py`의 10초 마감이 checkpoint flush 시간보다 짧았다.
- **늦은 spike가 기준에서 재현됐다.**
  - 기준 r503의 u8~u19 12개 표본 모두에서 vacuum 135~316M가 구간에 들어왔다.
  - 그때 호스트 전체가 100%였다(다른 사용자의 부하. 서버 CPU, sibling, 전체 모두).
  - worker instructions는 그대로였고(6,088.6M), 경과 시간과 worker CPU 시간은 두 배가 됐다(1.3초 → 2.5~2.9초, 1.0초 → 1.9~2.2초).
  - 후보 r503은 호스트가 조용했고, spike는 4번(98~128M)이었다.
- 이 결과로 10-28의 "유지 표본 4개 중 3개가 높다"와 같은 모양을 얻었다. 바쁜 호스트 아래에서 vacuum이 거의 매번 구간에 들어올 수 있다. 다만 호스트가 100%였던 다른 표본(기준 smoke s2~s4, 후보 c1 r8, 기준 h3 u0~u5)에서는 0~66M였다. 같은 "100%"라도 결과가 다르다.

### h3 (r600, client CPU 12와 52에 busy-loop)

- 가설은 이렇다. 계수 구간은 csql이 끝날 때 닫히므로, client가 느리면 COMMIT 뒤 구간이 길어지고 vacuum이 더 들어온다.
- 기준 r600 결과는 다음과 같다.
  - 호스트가 조용했던 u6~u9에서는 csql 경과 시간이 평소와 같았다(1.33~1.48초). csql은 거의 서버 응답을 기다리며 자고 있어서, 깨어나면 hog보다 먼저 CPU를 받는다. 그래서 이 조작으로는 client를 느리게 하지 못했다.
  - 같은 block의 u0~u5에서는 다른 사용자의 부하로 호스트가 100%였고, vacuum 7~66M가 들어왔다.
- 후보 r600은 harness 오류로 멈췄다. perf가 thread 하나를 두 번 적었고(한 줄은 `<not counted>`), 파서가 거부했다. 파서는 고쳤고, 실패한 파일로 다시 읽어 확인했다. 후보 h3는 다시 돌리지 않았다.
- 결론적으로 가설은 지지도 반박도 되지 않았다. 늦은 spike의 크기는 설명되지만, 정확한 시점 메커니즘과 빈도는 열린 질문이다.

### 기각한 가설

- **크기 기준 checkpoint (서버를 block마다 새로 띄우는 조건).** 서버를 띄울 때 다음 checkpoint 지점이 "현재 append + 100,000쪽"으로 정해진다(`log_manager.c:1506`). block 하나는 로그를 약 57,000쪽 쓴다. 오류 로그에는 checkpoint 메시지가 없어서 `events.py`로는 볼 수 없다. 오래 떠 있는 서버는 L1에서 본다.
- **log archive 생성.** c1에서 archive 생성이 UPDATE 구간 안에 6번(한쪽당 3번) 들어왔다. 초과는 −15.7~+28.9M였다. 10-28 +5.0158% 표본 세 개의 시각(19:24:19~19:24:50)에도 archive가 없었다.
- **호스트가 느린 것 자체.** 기준 smoke s2~s4는 호스트 100%, IPC 1.09~1.12에서도 초과가 없었다. h1, h2도 같다.

### 10-28, 10-29 표본

- 10-28 +5.0158%. 하위 에이전트가 정리한 자료와 시각을 맞춰 보면 postprofile 표본 s1~s4(19:24:19~47)다. 유지 표본 4개 중 3개가 +110M, +305M, +361M였다. 크기는 vacuum race 범위(후보 전체 약 425M) 안이다. 당시에는 thread별 자료가 없다. 명세는 이를 "later plain batch"라고 부른다.
- 10-28 후보 postprofile 표본은 매번 vacuum thread 9개가 새로 생겼다. 기준은 새로 생긴 thread가 없었다. 표본 간격(후보 9~10초, 기준 약 6.5초)과 idle timeout(5초) 때문이라고 추론했지만 시험하지 않았다. 후보 쪽 차이일 수도 있다.
- 10-29 +3.84%(fd8624c, UR candidate ordinary-r1 update-2). 같은 block의 다른 표본보다 +133M 높았고 IPC는 1.92였다. 크기는 vacuum race 범위 안이다. thread별 자료가 없어 확인할 수 없다.

## 환경과 재현 정보

| 역할 | 위치 | commit |
|---|---|---|
| 기준 | `/home/vimkim/gh/cb/oos-update-base-4781495`, 설치본 `~/.cub/install/oos-update-base-4781495/release_gcc` | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| 후보 | `/home/vimkim/gh/cb/CBRD-27816-ordinary-update`, 설치본 `~/.cub/install/CBRD-27816-ordinary-update/release_gcc` | `4c3c8d791ee619ad61701eff9555bc9ef27d9994` |

| 파일 | 기준 sha256 앞 16자 | 후보 sha256 앞 16자 |
|---|---|---|
| `bin/cub_server` | `addc5cff118521b8` | `3da7acf15fdac616` |
| `lib/libcubrid.so.11.5` | `19361b5f089fc873` | `13cc18507a0820a2` |
| `bin/csql` | `4d83a15290cea9b1` | `d4c7ebecc9dfa276` |

- 전체 값과 build ID는 `base/build.json`, `cand/build.json`에 있다. block마다 다시 확인했다.
- compile flag는 공통 파일 565개에서 모두 같다. 후보에만 OOS 파일 6개가 더 있다.
- 설정 `[common]`은 양쪽이 같다. `data_buffer_size=4G`, `log_buffer_size=256M`, `sort_buffer_size=16M`, `max_clients=50`, `db_volume_size=2G`, `log_volume_size=1G`, `log_max_archives=0`이다. live 값은 block마다 `lifecycle-r*/parameters.stdout`에 남는다.
- DB는 `u816b`(기준)와 `u816c`(후보)다. 데이터 2GiB, 활성 로그 1GiB다. 설치된 `cub-workenv`는 64M/32M로 만들기 때문에, 그 한 줄만 바꾼 사본(`sized-workenv/`)으로 만들었다. 처음에 32M로 잘못 만든 내 DB 두 개는 지웠다. 그 생성 기록은 `stale-createdb-records/`로 옮겨 보존했다.
- 서버는 CPU 16~19, client는 CPU 12에 고정했다. block마다 서버를 새로 띄우고 DB는 이어서 쓴다. 쌓인 log archive(각 12개)와 자동 확장 볼륨(각 2개)은 양쪽이 같다.
- 계수 명령은 `perf stat --per-thread -x ; -e instructions:u,cycles:u,task-clock -p SERVER -- csql ...`이다. `ordinary.py`와 구간과 event가 같고 `--per-thread`만 다르다. 구간 중에 생긴 thread의 계수는 부모 thread 줄에 합쳐진다.
- `block2.py`는 h2→p1→t1 실행 중에 고쳤다. 그 실행들의 환경변수 조합에서는 동작이 같도록 고쳤고, 고친 뒤 구문 검사를 했다. 다만 manifest의 harness 해시는 block마다 다르다(예: base r200과 cand r200).

## 실행 기록

| 이름 | 내용 | block | 결과 |
|---|---|---|---|
| smoke0 | 양쪽 1 block | 2 | 정상 |
| c1 | ABBA 8라운드, 경합 없음 (r1~r8) | 16 | 모두 완료, 실패 0 |
| h1 | 서버 CPU 경합 (r100, r101) | 4 | 모두 완료, 실패 0 |
| h2 | sibling 메모리 hog (r200, r201) | 4 | 모두 완료, 실패 0 |
| p1 | profile period 1M (r400, r401) | 4 | 완료. throttle로 표본 약 40% 손실, 쓰지 않음 |
| t1 | 꼬리 3초 계수 (r300, r301) | 4 | 모두 완료, 실패 0 |
| p1b | profile period 3M, block당 UPDATE 10개 (r410, r411) | 4 | 완료 |
| p3 | 꼬리 3초 profile period 3M (r420, r421) | 4 | 완료 |
| l1 | 서버 한 번에 UPDATE 20개 (r500) | 2 | 기준 완료. 후보는 UPDATE 10개 뒤 idle 10초 마감 실패. 캠페인 중단, r501 안 돎 |
| l1b | 서버 한 번에 UPDATE 20개, idle 마감 120초 (r503) | 2 | 모두 완료 |
| h3 | client CPU 12, 52 경합, UPDATE 10개 (r600) | 2 | 기준 완료. 후보는 perf 중복 줄로 harness 실패(파서 고침), 다시 돌리지 않음 |

명령은 다음과 같다. 모두 `/mnt/nvme/data-5/tmp/CBRD-27816-20261103`에서 실행했다.

```sh
python3 harness/campaign.py c1 1 8 5
BLOCK_HOG_CPUS=16,17,18,19 python3 harness/campaign2.py h1 100 2 5
BLOCK_HOG_CPUS=56,57,58,59 BLOCK_HOG_KIND=mem python3 harness/campaign2.py h2 200 2 5
BLOCK_THREADS=threads2.py BLOCK_EXTRA_ARGS="--tail 3" python3 harness/campaign2.py t1 300 2 5
BLOCK_MODE=profile BLOCK_EXTRA_ARGS="--period 3000017" python3 harness/campaign2.py p1b 410 2 10
BLOCK_MODE=profile BLOCK_PROFILE=profile2.py BLOCK_EXTRA_ARGS="--period 3000017 --tail 3" python3 harness/campaign2.py p3 420 2 6
python3 harness/campaign2.py l1 500 2 20
BLOCK_THREADS=threads3.py BLOCK_EXTRA_ARGS="--idle-deadline 120" python3 harness/campaign2.py l1b 503 1 20
BLOCK_HOG_CPUS=12,52 python3 harness/campaign2.py h3 600 1 10
python3 harness/analyze.py . --rounds smoke0,1,2,3,4,5,6,7,8
python3 harness/spikes.py . --threshold-m 15
python3 harness/profile_inclusive.py . 410,411 --comm transaction
python3 harness/profile_inclusive.py . 410,411 --comm transaction --under heap_oos_finalize_record
python3 harness/profile_inclusive.py . 420,421 --comm vacuum --plain-base 389.2 --plain-cand 423.8
```

## 열린 질문

- transaction worker가 15.9M 간격의 두 값으로 갈리는 이유. run 1과 4가 높은 값일 때가 많다.
- 첫 UPDATE(warmup)가 worker에서 약 +50~66M 더 쓰는 이유. 양쪽에 같다.
- C(`heap_update_logical` +51.2M)의 원인 코드.
- 질의 실행 밖의 약 +27M.
- vacuum 시작과 csql 종료 사이 시간. 10-28처럼 spike가 잦은 조건.
- 10-28 후보 쪽에서만 vacuum worker가 매번 새로 생긴 이유.
- 같은 표를 연속으로 UPDATE하는 측정(명세 항목)은 하지 않았다.

## 검토에서 나온 주의 사항

reviewed by Sonnet 5.5. 작업 모델(Opus 5.5)과 같은 Claude 계열이다. 이 환경에는 다른 계열 모델이 없다.

1. **(정정함) worker 차이 +94.2M는 중앙값 오류였다.** 두 덩어리 비율 차이 때문이다. 같은 run 위치끼리는 +86.2M다. h1, h2의 +94.0M, +99.2M도 같은 이유로 믿기 어렵다.
2. **(정정함) profile 환산에 위의 중앙값을 썼다.** 표본 합계 기준으로 다시 계산했다. throttle 손실은 약 0.2%로 작았다.
3. **(정정함) A·B·C 표가 닫히지 않았다.** 셋이 겹치지 않음을 `--under`로 확인했고(합 약 +166M), 줄어든 쪽(약 −87M)은 정확히 닫지 못했다고 적었다. record 만들기의 짝은 소스로 확인했다. C는 원인 코드를 특정하지 못했다.
4. **(정정함) spike B 재분류의 근거.** thread 생성은 결정 근거가 아니었다(150개 중 70개 표본에서 생김). vacuum-master 자신의 CPU tick 1개가 근거다.
5. **(반영함) vacuum race는 크기를 설명하지만 빈도는 설명하지 못한다.**
6. **(반영함) 10-29 +3.84% 표본**을 보고서에 넣었다.
7. **(일부 반영) 명세의 "늦은 이력 재현"과 "연속 UPDATE 측정".** L1과 L1b로 오래 떠 있는 서버를 쟀고, 기준에서 늦은 spike를 재현했다. 같은 표를 연속으로 UPDATE하는 측정은 하지 않았다.
8. **(반영함) checkpoint 기각의 범위**를 "block마다 새 서버" 조건으로 좁혔다.
9. **(반영함) t1은 vacuum 양을 보였을 뿐 경쟁 시점은 재지 않았다.** 또 statdump의 vacuum 계수는 쓸 수 없다. 100M가 넘는 vacuum 표본에서도 변화가 0이었다.
10. **(기록함) 운영상 주의.**
    - 실행 중에 `block2.py`를 고쳤다.
    - p1은 sample rate 상한을 확인하지 않고 돌려 4 block을 버렸다.
    - hog를 건 CPU에 다른 사용자의 작업이 있는지 확인하지 않았다.
11. **(기록함) 결정 기록의 시각이 몰려 있다.** 여러 행을 나중에 한꺼번에 적었다.

## 산출물

- 산출물 디렉터리 `/mnt/nvme/data-5/tmp/CBRD-27816-20261103/`. 아래 상대 경로는 이 디렉터리 기준이다
- 결정 기록 `decisions.tsv`
- 측정과 분석 스크립트 `harness/` (`threads.py`, `threads2.py`, `block.py`, `block2.py`, `campaign.py`, `campaign2.py`, `profile.py`, `profile2.py`, `analyze.py`, `spikes.py`, `events.py`, `profile_diff.py`, `profile_inclusive.py`)
- 표본 원자료 `base|cand/threads-r*/`, profile 원자료 `base|cand/profile-r*/`
- profile 분석 결과 `p1b-transaction-inclusive-raw.txt`, `p1b-under-heap_update_logical.txt`, `p3-vacuum-inclusive.txt`
- 호스트 CPU 1초 기록 `*-host.jsonl`
