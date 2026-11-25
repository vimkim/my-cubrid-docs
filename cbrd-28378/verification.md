# CBRD-28378 OOS bestspace hint 수정 검증 보고서

- 이슈: [CBRD-28378](https://jira.cubrid.org/browse/CBRD-28378) (상위 CBRD-26978, 관련 CBRD-28379·CBRD-28377)
- 작성일: 2026-11-25 (Asia/Seoul)
- 소스: `CUBRID/cubrid` `develop` `ca39c2c6a48df0bbc689c4d8b8d640113bb87d3e` 기준, 수정 커밋 `d9d641fbac` (브랜치 `CBRD-28378`, 아직 push하지 않음)
- 독자: 이 수정의 PR 리뷰어, CBRD-28379(page buffer 쪽 수정) 담당자

## 질문과 결론

**질문**: OOS 쪽 수정만으로, 동시 OOS INSERT가 할당 직후의 OOS 페이지를 조건부 latch로 서로 노리다 버퍼 프레임을 LRU 밖(VOID 영역)에 버리는 현상이 사라지는가? 공간 사용이 나빠지지 않는가?

**결론**: 사라진다. 이슈의 작은 재현(10세션 × 200KB 값 40행)에서 수정 전 빌드는 같은 부하에서 400행 중 94~147행만 넣고 10개 세션이 모두 멈췄으며, 1024개 프레임 중 929~946개가 VOID 영역의 `PAGE_OOS` 프레임이었다. 수정 후에는 400행이 0.53~0.60초에 모두 들어가고 VOID 프레임이 0개였다. 5배 규모(2000행)도 7.2초에 예외 없이 끝났다. 동시 INSERT에서 페이지 공유도 최적으로 유지되었다.

**열린 질문**: page buffer 쪽 결함(거절된 조건부 요청이 `waiter_exists` 를 남기는 문제)은 그대로 있다. OOS의 다른 조건부 fix 경로(bestspace sync, reclaim)와 heap 등 다른 모듈은 드물게 같은 누수를 낼 수 있으므로 CBRD-28379가 필요하다. QA shell_long `bug_3627` 전체는 로컬에서 돌리지 않았다.

## 원인 (develop `ca39c2c6a4` 소스 기준)

모든 줄 번호는 수정 전 `src/storage/oos_file.cpp` 기준이다.

1. `oos_find_best_page ()` 는 쓸 만한 페이지가 없으면 새 페이지를 할당한다. 그리고 WRITE latch를 쥔 채로 그 페이지의 빈 공간(페이지 전체)을 `oos_stats_add_bestspace ()` 로 공유 hash에 넣는다(3298-3309행). 호출자는 곧바로 그 페이지에 chunk를 쓰므로 이 hint는 처음부터 잘못된 정보다.
2. 호출자(`oos_insert_within_page ()`, `oos_insert_single_page_batch ()`)는 insert 뒤 남은 공간도 latch를 쥔 채로 공개한다(2294행, 2647행). 기존 페이지를 hash에서 찾은 경우에도 Phase C가 latch를 쥔 채 hint를 실제 빈 공간으로 다시 넣는다(754행 부근).
3. `oos_stats_find_page_in_bestspace ()` 의 Phase A는 `mht_get2 (vfid_ht, vfid, NULL)` 로 늘 그 파일의 **첫** hint만 읽는다. Phase C의 조건부 fix가 거절되면 `notfound_cnt` 만 늘리고 다시 같은 첫 hint를 고른다. 그래서 바쁜 페이지 하나를 lookup 한 번이 최대 `BEST_PAGE_SEARCH_MAX_COUNT`(100)번 다시 노리고, 그 뒤의 다른 hint는 보지 못한다. 이슈에서 400행 동안 집계된 조건부 fix 거절 5114회가 이 경로였다.
4. page buffer는 거절된 조건부 요청에도 `waiter_exists` 를 남기고, 소유자가 놓을 때 이 표시 때문에 LRU 배치를 건너뛴다(CBRD-28379). 할당 직후 VOID 영역에 있던 프레임은 어느 LRU 목록에도 들어가지 못한다.

## 수정 내용 (커밋 `d9d641fbac`)

불변식: **bestspace hint(hash와 헤더 `best[]`)는 다른 스레드가 WRITE latch로 쥐고 채우거나 지우는 중인 OOS 페이지를 가리키지 않는다.** hint는 조언일 뿐이고, lookup은 언제나 latch 아래에서 페이지를 다시 확인한다.

| 위치 | 변경 |
| --- | --- |
| `oos_find_best_page ()` | 새 페이지를 hash에 넣지 않는다. 함수 주석에 호출자 계약을 적었다. |
| `oos_stats_find_page_in_bestspace ()` Phase C 성공 | hint를 갱신하지 않고 회수한다(claim). hash hint는 지우고, `best[]` 에서 찾았으면 그 칸을 비운다. `best[]` 는 호출자가 쥔 헤더 페이지 WRITE latch가 보호한다. |
| 같은 함수 Phase A | `mht_get2` 커서로 hint를 차례로 훑는다. 바쁜 hash 후보는 lookup 안의 배열(최대 16개)에 기록하고 건너뛴다. hint는 hash에 남긴다(소유자가 insert가 아닐 수 있으므로). 항목을 지울 때는 커서를 직전 항목으로 되돌린다. |
| `oos_insert_within_page ()`, `oos_insert_single_page_batch ()` | 남은 공간을 latch 아래에서 재고, `auto_page_ptr.reset ()` 으로 latch를 놓은 **뒤** 공개한다. |
| `oos_delete_chain ()` → `oos_stats_update ()` | delete도 빈 공간을 latch 아래에서 재고, unfix 뒤 공개한다. `oos_stats_update ()` 는 page 대신 VPID와 빈 공간을 받는다. 데이터 페이지 latch를 쥔 채 헤더 페이지를 조건부 latch하던 중첩도 사라졌다. |
| 단위 테스트 seam(`CUBRID_UNIT_TEST_ENABLED` 전용) | `oos_test_bestspace_set_busy_page ()`, `oos_test_bestspace_hint_freespace ()`, 디버그 카운터 `bestspace_busy_candidates`. |

WAL, undo/redo, reclaim의 emptied-page 집합, vacuum sysop(OOS-ADR-0008)에는 변경이 없다. bestspace는 로그를 남기지 않는 메모리 캐시다. 락 순서도 새로 생기지 않는다. `bestspace_mutex` 는 여전히 말단 락이고, 공개는 latch 없이 잡는다.

## 실행 환경

- 빌드: CMake preset `release_gcc_unit`(GCC RelWithDebInfo, OOS·SPAGE·PAGE_BUFFER 단위 테스트 켬), Linux 80코어.
- 부하: 첫 수정 전 측정 때 load average 약 229, 그 뒤 측정들은 약 16~25. 수정 전·후 비교는 같은 부하(약 21~25)에서 다시 쟀다.
- DB: 전용 work environment, `data_buffer_size=16m`, `enable_string_compression=n`(이슈의 작은 재현과 같음). 실행마다 DB를 새로 만들었다.

### 재현 절차

```bash
db=voidc
csql -u dba -C -c "drop table if exists t; create table t (a int primary key, b varchar)" $db
for j in $(seq 1 10); do
  for i in $(seq 1 40); do echo "insert into t values ($((j*10000+i)), repeat('y', 204800));"; done > c$j.sql
done
for j in $(seq 1 10); do timeout 240 csql -u dba -C -i c$j.sql $db > c$j.log 2>&1 & done; wait
csql -u dba -C -c "select count(*) from t" $db
```

VOID 프레임 수는 서버에 gdb를 잠시 붙여, `pgbuf_Pool.BCB_table[i].flags` 의 영역 비트가 `PGBUF_VOID_ZONE` 인 프레임을 세어 확인했다(fix 수, dirty, `waiter_exists`, page type도 함께 셌다).

## 결과

### 동시 OOS INSERT (10세션 × 40행 × 200KB)

| 빌드 | load avg | 결과 | 세션 | VOID 프레임 (1024 중) |
| --- | --- | --- | --- | --- |
| 수정 전 `ca39c2c6a4` (1차) | 약 229 | 400행 중 147행, 240초 뒤 중단 | 10개 모두 시간 초과 | 929 (모두 `PAGE_OOS`, fix 0, dirty 182) |
| 수정 전 `ca39c2c6a4` (2차) | 약 21~25 | 400행 중 94행, 180초 뒤 중단 | 10개 모두 시간 초과 | 946 (모두 `PAGE_OOS`, fix 0, dirty 387) |
| 수정 후 `d9d641fbac` (4회) | 약 16~25 | 400행, 0.53~0.60초 | 10개 모두 정상, 오류 0 | 0 |
| 수정 후, 10세션 × 200행 | 약 17 | 2000행, 7.2초 | 10개 모두 정상, 오류 0 | 0 |

수정 전 1차 측정 직후 statdump는 `Num_data_page_victim_candidate = 21`, `Num_data_page_lru3 = 38` 이었다. 버퍼 풀 대부분이 어느 LRU 목록에도 없었다는 뜻이다.

### 공간 사용 (수정 후, `SHOW HEAP OOS OF t`)

| 작업 | OOS 레코드 | OOS 페이지 | 판단 |
| --- | --- | --- | --- |
| 10세션 × 300행 × 6KB | 3000 | 1501 | 페이지당 2개(6KB 값은 16KB 페이지에 2개까지 들어감). 최적이다. |
| 10세션 × 40행 × 200KB | 5200 chunk | 5201 | 값마다 chunk 13개. 약 9KB의 꼬리 chunk 두 개는 한 페이지에 들어가지 않으므로 페이지당 1개가 최적이다. |

동시 INSERT 중에는 채우는 중인 페이지가 hint에서 빠진다. 수정 전에도 그 페이지는 보였지만 latch를 얻을 수 없었으므로, 다른 세션은 결국 다른 페이지를 골랐다. 위 수치에서 이 변경으로 인한 단편화는 보이지 않는다.

### 단위 테스트 (ctest, 74개)

- 수정 후 최종 빌드: **74개 모두 통과**.
- 새 테스트(`unit_tests/oos/test_oos_bestspace.cpp`):
  - `BestspaceNewPageNotAdvertisedWhileLatched`: 할당한 새 페이지는 latch를 쥐는 동안에도, lookup만으로도 hint에 오르지 않는다. insert는 latch를 놓은 뒤 남은 공간을 공개한다.
  - `BestspaceReusedPageHintWithdrawnWhileLatched`: lookup이 가져간 페이지의 hint는 그 동안 hash에서 빠진다.
  - `BestspaceBusyHintTriedOncePerLookup`: 바쁜 hint는 lookup 한 번에 한 번만 시도하고, hint는 남기며, 다음 hint 페이지를 돌려준다. 두 페이지를 번갈아 바쁘게 만들어, 적어도 한 번은 바쁜 페이지가 먼저 나오는 것을 확인한다. 수정 전 lookup은 이 경우 바쁜 페이지만 100번 시도하고 `NOTFOUND` 를 돌려준다.
- 바꾼 테스트: `BestspaceFindBestPageConsecutiveCalls` 는 "lookup이 새 페이지를 공개한다"는 옛 계약에 기대었다. 새 계약(호출자가 unfix 뒤 공개)에 맞게 고쳤다.
- 리뷰 반영 전 빌드(1차 ctest)에서 `test_oos_real_vacuum_latch_timeout_retry` 가 60초 제한에 걸린 적이 있다. 이때 load average가 약 229였다. 이 테스트는 안에서 vacuum을 최대 60+120+30초 기다린다. 부하가 내려간 뒤 최종 빌드에서는 11.3초에 통과했다.

### 형식과 정적 검사

- `git diff --check` 깨끗함. `.github/workflows/codestyle.sh` 의 astyle 옵션으로 바뀐 세 파일 모두 차이 0. pre-commit codestyle hook 통과.
- `cubrid-static-check origin/develop d9d641fbac`: cppcheck 새 결과 0, 중복 코드 0. clang-tidy는 수정 전·후 모두 `oos_file.cpp` 를 처리하지 못해 결과가 없다(도구 문제). lizard: `oos_stats_find_page_in_bestspace ()` 의 CCN이 34에서 44로 늘었다. 바쁜 후보 건너뛰기와 테스트 seam 분기 때문이며, 결함은 아니다.

## 독립 리뷰

별도 agent가 읽기 전용으로 리뷰했다. blocker는 없었다.

| # | 지적 | 처리 |
| --- | --- | --- |
| 1 | delete 경로(`oos_delete_chain ()` → `oos_stats_update ()`)가 latch를 쥔 채 hint를 공개한다. vacuum이 디스크에서 막 읽은 페이지면 같은 누수가 날 수 있다. | 수정함. unfix 뒤 공개한다. |
| 2 | 헤더 `best[]` 에서 가져간 페이지는 `best[]` 에 남아, 다음 lookup이 노린다. | 수정함. Phase C 성공 때 그 칸을 비운다. |
| 3 | hint를 회수한 뒤 다시 넣을 때 전역 hash(1000개)가 가득 차면 hint를 잃을 수 있다. | 받아들임. hint는 조언이고, 함수 주석에 적었다. |
| 4 | unfix 뒤 공개하므로 더 최신 값을 덮어쓸 수 있다. | 받아들임. 같은 이유. lookup이 latch 아래에서 다시 확인한다. |
| 5 | 재사용한 페이지에서 insert가 실패하면 그 hint가 사라진다. | 받아들임. 페이지가 새거나 비었으면 emptied-page 집합이 맡는다. |
| 6 | 테스트 seam이 이전 오류 코드를 읽을 수 있다. VPID는 원자 변수가 아니다. | 수정함. seam에서 `er_clear ()`, release/acquire 순서, 단일 스레드 사용을 주석에 적음. |
| 7 | 바쁜 hint 테스트가 hash 순서에 기대어 두 번 다 그냥 통과할 수 있다. | 수정함. 적어도 한 번은 바쁜 페이지를 먼저 만났음을 확인한다. |
| 8 | sync scan·reclaim의 조건부 fix도 같은 누수를 낼 수 있다. | 범위 밖. CBRD-28379에 남긴다. |

## 제한 사항

- QA shell_long `bug_3627` 전체(100MB 버퍼, 40만 행 적재, 10세션 × 5000건)는 로컬에서 돌리지 않았다. 이슈의 작은 재현이 같은 VOID 누수를 재현하므로 이를 근거로 삼았다.
- 측정 장비는 다른 작업과 공유되어 부하가 크게 변했다. 수정 전 빌드는 부하와 무관하게 멈췄다(누수로 인한 정지). 절대 시간보다 멈춤과 VOID 프레임 유무를 비교하는 것이 의미 있다.
- page buffer 쪽 결함은 그대로다. 이 수정은 OOS insert·delete가 쥔 페이지로 조건부 fix가 몰리는 일을 없앤다. 다른 경로의 드문 조건부 fix 거절은 여전히 VOID 프레임을 남길 수 있다.
