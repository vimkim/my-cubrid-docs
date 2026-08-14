# PR #7157 — Option 1 (출력 단 clamp) vs Option 2 (카운터 게이트 통일) 비교 평가

PR: https://github.com/CUBRID/cubrid/pull/7157
JIRA: https://jira.cubrid.org/browse/CBRD-26500
분석 기준 커밋: `f3be52d2f` (PR HEAD, 2026-05-11)
관련 문서: [PR-7157-explanation.md](./PR-7157-explanation.md) (근본 원인·대안 비교 원본)
작성: Claude (Fable 5), 2026-08-14 — 코드 근거는 전부 `f3be52d2f` 기준 file:line 으로 검증함

리뷰 스레드에서 hornetmj 가 "보통 `pb_fetches > pb_ioreads` 일 텐데 왜 아닌 경우가 생기나?" 를 물었고, 답글에서 두 가지 해결 방향이 정리되었다. 이 문서는 그 두 옵션을 코드 레벨에서 비교 평가한다.

## TL;DR — Verdict

**Option 1 (출력 단 clamp, 현재 PR에 반영된 방식)이 우월하며, Option 2 는 단독으로는 버그를 못 고치고 보완재로서도 비용 대비 효용이 없다.**

핵심 근거: 두 카운터(`fetches`, `ioreads`)가 어긋나는 원인은 **최소 4가지**인데, Option 2 는 그중 **1가지(추적 활성화 시점 비대칭)만** 제거한다. 나머지 3가지 — 특히 매 interval 마다 재발하는 **스냅샷 straddle** — 가 남아 있는 한 clamp 는 어차피 필수다. clamp 가 들어간 뒤에는 Option 2 가 관측 가능한 개선을 만들지 못하면서, 사용자 가시 통계(`Num_data_page_ioreads`)의 의미 변경과 최고 핫패스 함수 수정이라는 리스크만 추가한다.

권장: 본 PR 은 Option 1 로 종결 (이미 8인 승인 완료). Option 2 는 본 PR 에서 진행하지 않고, 굳이 남기려면 별도 저우선 티켓으로 분리하되 아래 §6 의 함정을 티켓에 명기.

## 1. 두 옵션의 정의 (리뷰 스레드 기준)

| | Option 1 — 출력 단 clamp | Option 2 — 게이트 통일 |
|---|---|---|
| 위치 | `perfmon_server_calc_stats()` (`perf_monitor.c:1924-1948`) | `pgbuf_claim_bcb_for_fix()` (`page_buffer.c:8227`) 외 |
| 내용 | ratio 계산 직전 `(a > b) ? (a - b) : 0` clamp | `IOREADS` 증가를 `FETCHES` 와 동일한 캐싱값 `perf->is_perf_tracking` 으로 게이팅 |
| 상태 | PR 에 반영 완료 (`b92a5c8b0` + `f3be52d2f`) | 설계 스케치만 존재 (미구현 — 로컬 브랜치 `cbrd-26500-option2-gate-unify` 는 develop 포인터일 뿐 커밋 없음) |
| 성격 | 증상 억제 (소비 지점에서 불변식 강제) | 원인 일부 제거 (카운터 쌍의 일관성 개선) |

## 2. 왜 `ioreads > fetches` 가 되는가 — 어긋남 원인 4종 인벤토리

`PSTAT_PB_NUM_FETCHES` 증가 지점은 **전 코드베이스에 단 한 곳**: `pgbuf_fix()` 성공 경로의 `page_buffer.c:2400`. 반면 `PSTAT_PB_NUM_IOREADS` 의 살아있는 증가 지점은 `pgbuf_claim_bcb_for_fix()` 의 `page_buffer.c:8227` 하나다 (`page_buffer.c:4551` 은 `ENABLE_UNUSED_FUNCTION` 안의 죽은 코드). 이 두 지점의 게이팅·시점·도달 경로 차이에서 4가지 어긋남이 나온다.

### S1. 추적 활성화 시점 비대칭 — Option 2 의 타깃

- `FETCHES`: `pgbuf_fix()` 진입 시점에 `perf.is_perf_tracking = perfmon_is_perf_tracking()` 으로 **캐싱** (`page_buffer.c:2112`) → 증가 여부는 이 캐싱값으로 판정 (`page_buffer.c:2396-2400`).
- `IOREADS`: `perfmon_inc_stat()` 내부에서 증가 **시점에 라이브로** 재평가 (`perf_monitor.h:908-912`, `perfmon_is_perf_tracking()` = `pstat_Global.initialized && n_watchers > 0`, `perf_monitor.h:1466-1469`).

statdump 가 watcher 로 등록되어 추적이 켜지는 순간이 어느 fix 의 진입(시점 A)과 miss 처리(시점 B) 사이에 끼면, 그 fix 는 ioread 만 계상되고 fetch 는 누락된다. **발생 빈도: 추적 활성화당 1회성.**

### S2. 스냅샷 straddle (in-flight miss) — 매 interval 재발, Option 2 로 제거 불가

한 miss 의 `ioread++`(8227, 디스크 읽기 **전**)와 그 짝 `fetch++`(2400, latch 획득 **후**)는 항상 시간적으로 분리된다 (최소 디스크 읽기 지연만큼). `statdump -i` 의 값은 아래 §3 에서 보듯 **interval 간 diff** 이므로, 스냅샷 경계 T 에 걸친(in-flight) miss 는 ioread 가 interval N 에, fetch 가 N+1 에 귀속된다.

interval N 의 `hits_diff = fetches_diff − ioreads_diff = A − B + (진짜 hit 수)` 이다. 여기서 A = N 시작 시점 in-flight 수, B = N 종료 시점 in-flight 수. JIRA 재현 워크로드(10M × 10M 조인)처럼 **진짜 hit ≈ 0** 인 구간에서는 B > A 인 interval 마다 부호가 뒤집혀 wrap 이 발생한다. JIRA 스냅샷 `fetches = 33511, ioreads = 33512` — 정확히 1 차이 — 가 이 클래스의 전형이다.

**Option 2 를 완벽히 구현해도 이 원인은 그대로 남는다.** 두 증가 지점의 시간 분리는 게이팅 통일과 무관한, 계측 구조 자체의 성질이기 때문이다.

### S3. ioread 이후 실패 경로 — 영구 어긋남

`8227` 에서 ioread 를 계상한 뒤에도 fix 는 실패할 수 있다 (`dwb_read_page`/`fileio_read` 오류, 인터럽트 등 — `page_buffer.c:8239-8249` 및 이후 경로). 이때 `2400` 에 도달하지 못하므로 fetch 는 영영 계상되지 않는다. 실패 1건당 +1 의 **영구적** ioread 잉여. Option 2 와 무관하게 잔존.

### S4. `pgbuf_simple_fix` 구조적 어긋남 — fetch 를 아예 안 세는 경로

`pgbuf_simple_fix()` (`page_buffer.c:2475`, temporary volume 전용) 는 miss 시 `pgbuf_claim_bcb_for_fix(..., perf=NULL, ...)` 를 호출한다 (`page_buffer.c:2503`) → `8227` 의 ioread 는 계상되지만, 이 함수에는 FETCHES 증가가 **없다** (증가 지점이 2400 한 곳뿐이므로). 실제 호출자는 `query_manager.c:2722` (`need_fix=true`, 쿼리 temp 페이지) — 대형 정렬/임시 결과 워크로드에서 실동작하는 경로다. (`file_manager.c:4086, 4294` 는 `need_fix=false` 라 2503 에 도달하지 않음.)

즉 **현행 구조에서도 temp 페이지 miss 는 ioread 만 쌓는다.** Option 2 가 이걸 "고치는" 유일한 방법은 8227 을 `perf` 게이트로 감싸 이 경로의 ioread 계상을 **중단**하는 것인데, 그러면 실제 발생한 물리 읽기가 `Num_data_page_ioreads` 에서 빠진다 — ratio 하나 고치자고 원시 카운터의 의미를 바꾸는 셈이다 (§6).

## 3. statdump -i 데이터 흐름 — "interval diff 에서 ratio 계산" 의 근거

```
cubrid statdump testdb -i 1            (util_cs.c:2482, interval>0 이고 -c 없으면 cumulative=false)
  → histo_print_global_stats(cumulative=false)      (util_cs.c:2571 → network_histogram.cpp:299)
  → perfmon_print_global_stats()                    (perf_monitor.c:906)
      ├─ perfmon_get_global_stats()                 서버에서 누적 원시 카운터 수신
      ├─ perfmon_calc_diff_stats(diff, cur, old)    (perf_monitor.c:937 — 클라이언트 측)
      │    ├─ 카운터별 diff, new < old 이면 0 clamp (perf_monitor.c:1435-1442)  ← 카운터 단위 방어는 기존에 있었음
      │    └─ perfmon_server_calc_stats(stats_diff) (perf_monitor.c:1458)       ← ratio 는 diff 위에서 계산
      └─ perfmon_server_dump_stats(diff)            출력
```

두 가지 함의:

1. 카운터 **각각의** diff 는 이미 clamp 되어 있었지만(1435-1442), **카운터 간 뺄셈**(`fetches_diff − ioreads_diff`)은 무방비였다 — PR 이 메운 구멍이 정확히 여기다.
2. `perfmon_server_calc_stats()` 는 누적 경로(`xperfmon_server_copy_global_stats`, `perf_monitor.c:1056`)와 diff 경로(1458), 서버·클라이언트 양쪽 빌드 모두가 통과하는 **단일 초크포인트**다. Option 1 은 이 한 곳에서 모든 소비자를 커버한다.

## 4. 평가 매트릭스

| 기준 | Option 1 (clamp) | Option 2 (게이트 통일) |
|---|---|---|
| S1 제거 | ✅ (증상 차단) | ✅ (원인 제거) |
| S2 제거 | ✅ (증상 차단) | ❌ |
| S3 제거 | ✅ (증상 차단) | ❌ |
| S4 제거 | ✅ (증상 차단) | ⚠️ ioread 미계상으로 "제거" — 원시 카운터 의미 변경 |
| LOG_HIT_RATIO 커버 | ✅ 동일 clamp (`perf_monitor.c:1931-1936`) | ❌ 별도 설계 필요 (log 쪽은 fetch 2곳·ioread 4곳 모두 라이브 게이트, `log_page_buffer.c:902,1972` / `2069,2178,5310,5575`) |
| PAGE_ALLOCATE_TIME_RATIO 커버 | ✅ (`perf_monitor.c:1942-1948`) | ❌ 원리적으로 불가 — 세 시간 카운터는 서로 다른 지점에서 누적되어 straddle 이 본질적 |
| 핫패스 비용 | 0 (출력 단 1회 계산 경로만) | 사실상 0 (캐싱 bool 체크) — 성능은 논거 아님 |
| 원시 카운터 의미 | 불변 | `Num_data_page_ioreads` 계상 조건 변경 (§6) |
| 수정 파일/검토 표면 | `perf_monitor.c` 출력 함수 1곳 | `pgbuf_claim_bcb_for_fix`(최고 핫패스, ~300줄) + `pgbuf_simple_fix` 호출부 + blame 고고학 |
| 리뷰 상태 | 8인 승인 완료 | 미구현·미검토 |

## 5. clamp 의 잔여 부정확도가 무해한 이유

clamp 의 비용은 "어긋남 구간에서 hit ratio 가 0% 로 표시됨" 인데, 어긋남(S2)이 부호를 뒤집을 수 있는 조건 자체가 **진짜 hit 이 straddle 노이즈(수 건)보다 적은 구간**, 즉 실제 hit ratio ≈ 0% 인 구간이다. 반대로 hit 이 많은 정상 워크로드에서는 `fetches_diff ≫ ioreads_diff` 라 노이즈가 부호를 못 뒤집는다. **요컨대 clamp 가 0 을 출력하는 바로 그 순간의 참값이 ≈ 0 이다.** 남는 오차는 `±수 건 / fetches_diff` 수준의 지터로, 모니터링 지표가 본래 허용하는 클래스다.

## 6. Option 2 구현 스케치와 세 가지 함정

리뷰 스레드에서 합의된 스케치를 실제 diff 로 전개하면:

```c
/* page_buffer.c:8224 부근 */
  if (fetch_mode != NEW_PAGE)
    {
      /* Record number of reads in statistics */
-     perfmon_inc_stat (thread_p, PSTAT_PB_NUM_IOREADS);
+     if (perf != NULL && perf->is_perf_tracking)
+       {
+         perfmon_inc_stat (thread_p, PSTAT_PB_NUM_IOREADS);
+       }
      show_status->num_pages_read++;
```

**함정 1 — `perf=NULL` 경로의 딜레마 (`page_buffer.c:2503`).** 위 diff 그대로면 `pgbuf_simple_fix` 발 temp 페이지 miss 의 물리 읽기가 `Num_data_page_ioreads` 에서 통째로 빠진다 (현행은 계상됨). 이를 피하려고 `pgbuf_simple_fix` 에 perf 를 배관해도, 이 함수는 fetch 를 세지 않으므로 S4 의 어긋남은 그대로다 — 배관 작업만 늘고 목적은 달성 못 한다. 어느 쪽을 골라도 잃는 게 있다.

**함정 2 — clamp 없이는 버그가 재현된다.** S2·S3 이 남아 있으므로 Option 2 단독 배포 시 `4 × 10^12` 값은 (빈도만 줄어든 채) 계속 나온다. 즉 Option 2 는 clamp 의 **대체재가 될 수 없고**, clamp 가 있으면 Option 2 의 효과는 ratio 출력에서 관측 불가능하다. 어떤 조합을 골라도 Option 2 의 한계 기여는 "추적 활성화 직후 첫 interval 에서 0% 블립이 나올 확률 감소" 뿐이다.

**함정 3 — 검토 표면의 비대칭.** `pgbuf_claim_bcb_for_fix` 는 페이지 fix miss 경로의 심장부다. 모니터링 표시값 하나를 위해 이 함수의 통계 시맨틱을 바꾸는 변경은, 출력 함수 한 곳의 순수 산술 변경(Option 1)과 리뷰 리스크의 급이 다르다. 2503 호출부의 `perf=NULL` 이 의도적 통계 제외였는지 blame 확인도 선행되어야 한다.

## 7. 권장 액션

1. **본 PR 은 현재 상태(Option 1)로 종결.** greptile 지적(덧셈 오버플로 — `f3be52d2f`)까지 반영되어 있고 승인 8건 확보 상태.
2. **hornetmj 스레드에 후속 답글로 본 분석 요지 공유** — "옵션 2로도 진행해보겠습니다" 를 걸어둔 상태이므로, S2(스냅샷 straddle)·S4(`pgbuf_simple_fix`) 근거를 들어 "옵션 2는 활성화 비대칭(S1)만 제거하고 매 interval 재발하는 straddle 은 못 막으므로 clamp 가 어차피 필수이며, 옵션 2는 별도 티켓으로 분리(또는 드랍)" 로 정리하는 것이 기술적으로 정직하다.
3. Option 2 를 살리려면 **별도 저우선 티켓**으로: 제목은 "fetch/ioread 카운터 게이팅 일관성" 수준으로 한정하고, 본 문서 §6 함정 3종(특히 `Num_data_page_ioreads` 의미 변경 여부 결정)을 티켓 본문에 명기. 로컬 브랜치 `cbrd-26500-option2-gate-unify` 는 빈 포인터이므로 재사용하거나 삭제.

## Appendix — 근거 위치 총람 (`f3be52d2f` 기준)

| 사실 | 위치 |
|---|---|
| FETCHES 증가 (유일) | `page_buffer.c:2400` |
| FETCHES 게이트 (진입 시 캐싱) | `page_buffer.c:2112, 2396` |
| IOREADS 증가 (라이브 게이트) | `page_buffer.c:8227` |
| IOREADS 죽은 지점 (`ENABLE_UNUSED_FUNCTION`) | `page_buffer.c:4551` |
| `perfmon_add_stat` 라이브 재평가 | `perf_monitor.h:908-912` |
| `perfmon_is_perf_tracking` 정의 | `perf_monitor.h:1466-1469` |
| `pgbuf_claim_bcb_for_fix` 정의 / perf 있는 호출 / NULL 호출 | `page_buffer.c:8133 / 2191 / 2503` |
| `pgbuf_simple_fix` 정의·실호출자 | `page_buffer.c:2475`, `query_manager.c:2722` |
| statdump 루프 (interval 시 cumulative=false) | `util_cs.c:2482-2579` |
| 클라이언트 diff 계산 → ratio | `perf_monitor.c:906-944, 937, 1458` |
| 카운터별 diff clamp (기존) | `perf_monitor.c:1435-1442` |
| 누적 경로의 ratio 계산 | `perf_monitor.c:1050-1057` |
| 수정된 3개 ratio clamp | `perf_monitor.c:1924-1948` |
| LOG fetch/ioread 증가 지점 | `log_page_buffer.c:902, 1972 / 2069, 2178, 5310, 5575` |
| 리뷰 스레드 (hornetmj 질문·옵션 정리) | PR #7157 inline thread, 2026-05-11 |
| JIRA 스냅샷 `33511 vs 33512` | CBRD-26500 코멘트 (2026-01-21) |
