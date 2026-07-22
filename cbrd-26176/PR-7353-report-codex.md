# PR #7353 Code Review Report

**PR:** [CUBRID/cubrid#7353](https://github.com/CUBRID/cubrid/pull/7353)
**Title:** [CBRD-26176] Redesign bestspace
**Author:** hyahong
**Reviewer:** vimkim
**HEAD SHA:** `cc6bd0d6e3cb6b2f0d662da36c8049f0a2ad17fa`
**Review date:** 2026-07-22
**Verdict:** Request changes

> **TL;DR** (Blocking): 새 bestspace 구조는 heap header의 WRITE latch 병목을 shard 기반 메모리 구조로 옮기는 핵심 방향은 타당하고 전체 CI도 통과한다. 그러나 기존 11.5 DB의 heap header를 새 layout으로 바로 해석하는 disk compatibility 문제와 모든 요청이 shard 0, bias 0에서 시작해 분산 설계를 무력화하는 회귀가 있다. lazy cache 생성 전 free-space update 유실 및 SA_MODE 재접속 시 registry 잔존 문제도 확인했다. 네 경로를 보완하고 targeted 회귀/성능 테스트를 추가하기 전에는 merge하지 않는 편이 안전하다.

## Summary

- **Scope:** 34 files, +5,301/-3,020, 57 commits. `bestspace.cpp/.hpp` 신설과 `heap_file.c` 대규모 변경을 중심으로 buffer, vacuum, recovery, parallel scan, statistics, boot 경로까지 연결된다.
- **Intent:** heap header WRITE latch 아래 있던 bestspace 검색과 `num_pages`, `num_recs`, `recs_sumlen` 추정치 갱신을 shard별 lock-free atomic 구조로 분산한다.
- **Design:** shard당 64개 L1 page entry와 L2/L3 tier bitmap, 최대 128개 candidate queue, heap별 global registry와 thread-local cache, heap 내부 1-4개 persistent metadata page를 사용한다.
- **Positive:** bestspace metadata page를 user heap page 통계와 scan/vacuum/index-build 경로에서 제외했고, page latch 재정렬을 위한 ordered callback 및 종료 시 disk 동기화 경로를 추가했다.
- **Verification:** 동일 HEAD를 리뷰 전후 확인했다. Debug build 성공. CircleCI build/debug/sql/medium/shell과 GitHub style/static checks는 성공했다. 로컬 ctest에는 등록된 test가 없었다.
- **Merge gate:** testcase PR #2969와 private testcase PR #3529가 아직 open이라 `Check TC PRs`는 실패 상태다.

## Findings

### Blocking

1. `src/storage/heap_file.c:4415` - 기존 heap header format을 migration 또는 compatibility gate 없이 새 `HEAP_HDR_STATS`로 해석한다.

   `origin/develop`의 header는 작은 legacy `estimates` layout이고, 이 PR의 header는 `last_vpid`, 64-bit estimates, candidate 128개, shard/page metadata를 포함한 큰 layout이다. 그러나 disk compatibility level은 여전히 `11.5f`이고, `heap_build_bestspace()`는 record length가 정확히 새 구조체 크기라고 assert한 뒤 그대로 cast한다. 기존 11.5 DB를 열면 debug build는 assert할 수 있고, release build는 짧은 record 밖의 값을 `num_shards`, metadata VPID 등으로 읽을 수 있다. 새 layout을 읽기 전에 migration을 수행하거나 disk compatibility level을 올려 명확히 거부해야 한다.

2. `src/storage/bestspace.cpp:1360` - 모든 request가 shard 0과 동일 L1 bias에서 탐색을 시작한다.

   초기 구현은 `thread_ref.index % SHARD_COUNT`로 shard를, transaction index로 L1 탐색 bias를 분산했다. commit `2c7071fd`에서 unfill-space 계산을 추가하면서 두 값이 모두 0으로 바뀌었고 현재까지 유지됐다. 따라서 shard 0에서 page를 찾는 동안 다른 shard는 탐색되지 않고, 같은 L3/L2/L1 순서와 page latch에 요청이 다시 집중된다. shard 0이 allocation 중이거나 후보가 없을 때만 다음 shard로 진행하므로 JIRA의 shard 기반 load distribution acceptance를 충족한다고 보기 어렵다. thread/transaction 기반 시작점을 복원하고 shard별 request/found/allocated 분포를 검증해야 한다.

### Non-blocking (should fix before merge)

3. `src/storage/heap_file.c:4522` - lazy in-memory cache가 만들어지기 전에 발생한 free-space update가 사라진다.

   vacuum/physical delete 경로는 `heap_add_bestpage()`에서 `heap_find_bestspace(thread_p, NULL, ...)`를 호출한다. registry entry가 아직 없으면 이 함수는 lookup-only로 즉시 `NULL`을 반환하고 candidate를 버린다. 재시작 직후 insert보다 vacuum/delete가 먼저 공간을 회수하면, 뒤늦게 생성된 cache는 stale persistent snapshot만 읽어 새 page를 불필요하게 할당할 수 있다. page/header 정보로 entry를 생성하거나, cache가 없을 때도 candidate를 persistent/in-memory seed로 보존해야 한다.

4. `src/storage/bestspace.cpp:1840` - heap manager 종료 시 process-global registry와 TLS cache를 비우지 않는다.

   `bestspaces`는 process-global이고 destructor는 process exit에서만 실행된다. `heap_manager_finalize()`에는 reset/destroy-all hook가 없다. SA_MODE에서 한 DB를 종료한 후 같은 프로세스가 다른 DB를 열고 숫자 HFID를 재사용하면 `find()`가 이전 DB의 bestspace object를 반환할 수 있다. 이 경우 stale VPID, estimates, unfill, shard configuration이 새 DB로 넘어간다. heap manager lifecycle에 전체 registry reset과 generation 증가를 추가해 TLS entry도 무효화해야 한다.

## Test Gaps

- 기존 11.5 DB를 새 binary로 열어 첫 INSERT, statistics, compactdb까지 확인하는 upgrade/compatibility test가 없다.
- 다중 thread가 동일 heap에 INSERT할 때 shard별 `request`, `found`, `allocated`가 고르게 분산되는 test/수치가 없다.
- server restart 직후 cache miss 상태에서 vacuum/delete가 공간을 회수한 뒤 INSERT가 해당 page를 재사용하는 test가 없다.
- SA_MODE 한 프로세스에서 DB A 종료 -> DB B 시작, 동일 numeric HFID 재사용을 강제하는 lifecycle test가 없다.
- JIRA acceptance인 다중 transaction INSERT 부하 분산과 성능 향상을 수치로 증명하는 신규 benchmark 결과가 PR에 없다. 기존 TC PR들은 주로 출력 및 기존 testcase 보정이다.

## JIRA Context

- **CBRD-26176:** 다수 transaction이 동일 table에 INSERT할 때 heap header WRITE latch가 bestspace 검색 대부분을 직렬화하는 병목을 제거하는 구현 ticket이다. acceptance는 shard/lock-free 기반 부하 분산과 insert-heavy 성능 향상이다.
- **CBRD-26858:** Oracle freelist/ASSM과 PostgreSQL FSM을 참고한 조사/설계 ticket이다. bestspace뿐 아니라 `num_recs`, `recs_sumlen`, `last_vpid`, `num_pages`까지 header WRITE latch에서 분리해야 한다는 검토 의견이 있었고, PR은 이를 atomic estimates 및 별도 last-page 경로로 반영했다.

## Existing Comments

| Source | Topic | Status |
|---|---|---|
| Greptile | on-disk `std::size_t` portability | 작성자는 동일 platform 전제를 설명, bot은 필수 수정 의견 철회 |
| Greptile | registry mutex를 잡은 채 shutdown page I/O 수행 | shutdown-only precondition 설명 후 bot이 철회; precondition 문서화 권장 |
| Greptile | heap header disk format 변경 | 작성자는 release 사이 format 변경이 가능하다고 답변; compatibility level/migration 근거는 추가 확인 필요 |
| Greptile | `spage_get_record` error 설정 | callee가 error를 설정한다는 답변 후 종료 |
| Greptile | `er_clear()` 호출 | error 분기 순서를 설명한 뒤 bot이 철회 |

## Review Notes

- Native review는 `bestspace.cpp:1354-1355`의 slot overhead가 `spage_max_space_for_new_record()`와 이중 계산된다는 P2 후보도 제시했다. 실제 helper는 새 slot 공간을 이미 차감하므로 조건이 보수적인 것은 맞다. 다만 `origin/develop`도 `total_space = record + slot + unfill`을 같은 helper 결과와 비교하므로 이 PR이 새로 만든 회귀로 분류하지 않았다. tier boundary/page growth test로 별도 검증할 개선 후보로 남긴다.

## Review Questions

1. guava 11.5 내 minor upgrade에서 기존 DB를 그대로 여는 것이 지원 범위라면, `HEAP_HDR_STATS` migration과 disk compatibility bump 중 어느 정책을 적용할 것인가?
2. cache miss 중 free-space update를 버리는 동작이 의도적이라면, 언제 full scan이 stale snapshot을 회복하며 page bloat의 상한은 무엇인가?
3. SA_MODE multi-database lifecycle은 지원하지 않는다는 명시적 invariant가 있는가? 없다면 registry reset의 적절한 호출 시점은 어디인가?
4. 30초 주기 및 shutdown checkpoint 중 crash 시 persistent hints가 stale해도 correctness가 보장되는 invariant를 어떤 test로 검증했는가?

## Conclusion

핵심 설계는 기존 header latch 병목을 줄일 수 있는 구조지만, 현재 시작점 고정은 분산 효과를 약화하고 persistent format과 process/cache lifecycle은 운영 DB의 안전성에 직접 영향을 준다. Findings 1-4의 수정 및 targeted regression test, 그리고 JIRA acceptance에 대응하는 insert-heavy 분포/성능 수치를 확인한 뒤 재리뷰를 권장한다.
