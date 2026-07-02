# PR #7157 — [CBRD-26500] Fix uint64 underflow in page buffer hit ratio

PR: https://github.com/CUBRID/cubrid/pull/7157
JIRA: https://jira.cubrid.org/browse/CBRD-26500
Branch: `vimkim:data-pgbuf-hit-ratio-bugfix`
Commit: `b92a5c8b0`
Diff: 1 file (`src/base/perf_monitor.c`), +19 / −13.

이 문서는 PR 본문에서 분리한 보강 자료다. PR 본문은 짧게 유지하고, 아래 내용은 리뷰어가 더 깊이 보고 싶을 때 참조한다.

## 1. 문제 현상

`cubrid statdump demodb -i 1 | grep "Data_page_buffer_hit_ratio"` 결과에 정상 값(`87.06` 등)과 함께 비현실적인 값이 섞여 출력됨:

```
Data_page_buffer_hit_ratio = 4034632613888.00
Data_page_buffer_hit_ratio = 0.00
Data_page_buffer_hit_ratio = 4055477256192.00
Data_page_buffer_hit_ratio = 0.00
Data_page_buffer_hit_ratio = 4222865637376.00
```

(JIRA 본문 인용)

## 2. 근본 원인

`src/base/perf_monitor.c`의 `perfmon_server_calc_stats()`에서 다음 식을 사용:

```c
stats[pstat_Metadata[PSTAT_PB_HIT_RATIO].start_offset] =
  SAFE_DIV ((stats[...PSTAT_PB_NUM_FETCHES...]
             - stats[...PSTAT_PB_NUM_IOREADS...]) * 100 * 100,
            stats[...PSTAT_PB_NUM_FETCHES...]);
```

`stats[]`는 `UINT64`. `PSTAT_PB_NUM_FETCHES`와 `PSTAT_PB_NUM_IOREADS`는 페이지 fix 경로에서 별도 시점에 비원자적으로 증가:

| 카운터 | 증가 지점 (page_buffer.c) |
|---|---|
| `PSTAT_PB_NUM_FETCHES` | 2397 (fix path) |
| `PSTAT_PB_NUM_IOREADS` | 4548 (사용자 영역 IO 복사 경로) |
| `PSTAT_PB_NUM_IOREADS` | 8224 (BCB victim 경로) |

(2026-05 기준 `git grep` 결과 위 세 곳이 전부)

perfmon 집계 스레드가 `stats[NUM_FETCHES]`와 `stats[NUM_IOREADS]`를 락 없이 독립적으로 읽기 때문에, 한 워커 스레드가 ioreads는 이미 증가시켰지만 fetches 증가는 아직 안 한 윈도우에서 캡처되면 `ioreads > fetches` 상태가 노출된다. JIRA 코멘트(Daehyun Kim, 2026-01-21)의 스냅샷:

```
fetches = 33511, ioreads = 33512
```

이때 unsigned 뺄셈 `fetches - ioreads = 2^64 - 1`로 wrap → `* 10000` 모듈러 산술 → `/ fetches`를 거쳐 비현실적인 큰 수가 출력된다.

## 3. 수정

`perfmon_server_calc_stats()`의 세 ratio 계산식 직전에 양의 차분을 0으로 clamp:

| ratio | 식 | 위치 |
|---|---|---|
| `PSTAT_PB_HIT_RATIO` | `(a > b) ? (a - b) : 0` | `perf_monitor.c:1924-1929` |
| `PSTAT_LOG_HIT_RATIO` | `(a > b) ? (a - b) : 0` | `perf_monitor.c:1931-1936` |
| `PSTAT_PB_PAGE_ALLOCATE_TIME_RATIO` | `(a > b + c) ? (a - b - c) : 0` | `perf_monitor.c:1942-1948` |

수정 후 코드 형태 (PB 블록 예시):

```c
{
  UINT64 pb_fetches = stats[pstat_Metadata[PSTAT_PB_NUM_FETCHES].start_offset];
  UINT64 pb_ioreads = stats[pstat_Metadata[PSTAT_PB_NUM_IOREADS].start_offset];
  UINT64 pb_hits = (pb_fetches > pb_ioreads) ? (pb_fetches - pb_ioreads) : 0;
  stats[pstat_Metadata[PSTAT_PB_HIT_RATIO].start_offset] = SAFE_DIV (pb_hits * 100 * 100, pb_fetches);
}
```

## 4. 대안 비교 — 왜 카운터 atomic화가 아닌가

JIRA 코멘트의 임시 해결책 (a) `(a - b) * 100.0 * 100.0`, (b) `static_cast<uint64_t>((a - b) * 100.0 * 100.0)` 모두 wrap된 `uint64`(`≈ 1.8447 × 10^19`)를 `double`로 변환했다가 다시 `uint64_t`로 캐스트하는 경로를 거친다. 이 변환은 `C11 §6.3.1.4 ¶1`("If the value of the integral part cannot be represented by the integer type, the behavior is undefined")에 따라 정의되지 않은 동작이 될 수 있다. 본 PR의 정수 도메인 clamp는 이 UB 가능 경로 자체를 회피.

카운터를 `std::atomic<uint64_t>` / `lock xadd`로 보호하는 대안:

- 비용: x86에서 uncontended `lock xadd` ~20–30 cycle, 다중 워커 컨텐션 시 캐시 라인 바운싱 추가. 페이지 fix는 서버에서 가장 빈번한 이벤트 중 하나라 페널티가 영구 누적.
- 효용: 모니터링 ratio 한 줄의 wrap만 제거. hit ratio는 시스템 불변식이 아니라 베스트-에포트 관찰값이라 캡처 지터 자체는 본래 허용 범위.

→ 핫패스 비용 0인 출력 단 clamp가 비용/정확도 균형 면에서 우월. 본 PR 이후에도 비원자 캡처로 인한 작은 수치 노이즈(`fetches`가 `10^5–10^7` 자릿수일 때 노이즈 ~`1/fetches`)는 남지만, 이는 `4 × 10^12` 같은 unsigned wrap과는 다른 클래스의 문제.

## 5. 건드리지 않은 ratio (스코프 경계)

분자가 단일 카운터(뺄셈 없음)인 ratio들은 동일 클래스가 아니므로 의도적으로 손대지 않음:

- `PSTAT_PB_VACUUM_EFFICIENCY`
- `PSTAT_PB_VACUUM_FETCH_RATIO`
- `PSTAT_VACUUM_DATA_HIT_RATIO`

## 6. PB_PAGE_ALLOCATE_TIME_RATIO에 대한 참고

`fix_time`, `hold_time`, `lock_time`은 모두 `_10USEC` 단위 (10µs 누적, `2^64 / 10µs ≈ 5.85 × 10^6 년` 규모). 두 합이 `UINT64`를 넘는 상황은 사실상 발생 불가. 실제로 이 PR이 막는 위험은 비원자 캡처로 `fix_time < hold_time + lock_time`이 되는 부등식 위반 케이스로, PB/LOG의 `ioreads > fetches`와 구조적으로 동일한 클래스다.

## 7. 검증 결과 (작성자 머신)

| Run | Build | 샘플 | BAD | 값 범위 |
|---|---|---|---|---|
| Positive control (with fix) | release, 1M × 1M | 498 | 0 | `[0.00, 100.00]` |
| Negative control (without fix) | release, 1M × 1M | 540 | 0 | `[0.00, 100.00]` |

Positive control은 fix가 wrap을 차단함을 확인. Negative control은 1M 규모에서 race window를 통계적으로 노출하지 못함 — JIRA 원본 재현은 10M × 10M.

## 8. 권장 추가 검증

머지 전 10M 규모에서 negative control을 한 번 더 확인하면 좋음:

```sql
-- t1, t2 각각 10M
insert into t1 select rownum,
                      lpad(rownum,20,'0'), lpad(rownum % 5,20,'0'),
                      lpad(rownum,20,'0'), lpad(rownum,20,'0'),
                      lpad(rownum,20,'0'), lpad(rownum,20,'0')
              from db_class a, db_class b, db_class c, db_class d, db_class e
              limit 10000000;
```

```sh
# 셸 1
csql -u dba -C testdb -c "SELECT a.col1, a.col2, a.col3 FROM t1 a, t2 b
   WHERE a.col1 = b.col1 AND a.col2 = b.col2 AND a.col3 = b.col3
   ORDER BY 3, 2, 1;"

# 셸 2
cubrid statdump testdb -i 1 \
  | awk '/Data_page_buffer_hit_ratio|Log_page_buffer_hit_ratio|Data_page_allocate_time_ratio/ {
           v = $NF + 0;
           if (v > 100 || v < 0) print "BAD:", $0
         }'
```

기대: 본 패치를 일시적으로 되돌린 빌드에서 `BAD:` 라인이 1회 이상 출력될 것. fix된 빌드에서는 0건.

## 9. 후속 작업 후보

동형 패턴이 여러 번 반복되므로 `PSTAT_*_RATIO` 계산을 헬퍼 매크로/인라인으로 통합해 향후 신규 ratio 추가 시 같은 실수를 구조적으로 막는 리팩토링을 고려할 수 있음. 본 PR 범위 외.
