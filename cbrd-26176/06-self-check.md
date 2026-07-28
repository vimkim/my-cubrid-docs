# PR #7353 (CBRD-26176) Redesign bestspace — 이해도 셀프 체크

- **기준 커밋**: `e84a7f6dc` (develop `f30f1c260`) / **작성일**: 2026-07-28 / **작성 주체**: claude-fable-5
- 사용법: 01~05 문서를 다 읽은 뒤, **아무 자료도 보지 않고** 이 문서만으로 점검한다.
  하나라도 막히면 해당 문서 섹션으로 돌아간다. 정답은 맨 아래(스포일러 구분선 이후).

---

## A. 화이트보드 재현 체크리스트 (자료 없이 그릴 수 있어야 함)

1. **구조도**: registry(전역 리스트 + TLS 캐시) → bestspace(shard 배열 + candidate queue +
   atomic estimates) → shard(L3 1개, L2 8개, L1 64개, allocating bit) → on-disk
   (heap header의 bestspace 블록 + shard 페이지 slot 2)의 전체 대응 관계.
2. **INSERT 시퀀스 다이어그램**: qexec → locator → heap_insert_logical →
   heap_get_insert_location_with_lock → heap_find_bestpage → (registry 조회/lazy build)
   → (30s sync 분기) → bestspace::find → shard 순회 → L3→L2→L1 → L1_fix → CAS 선차감
   → FOUND(페이지 latch 보유) → slot 확보/lock → 물리 insert.
3. **allocate 흐름**: allocating bit → victim 4 → candidate pop → resident 재검증 →
   최대 후보 실측 검증 → 부족분 신규 4-n장 → L1 교체 → 반환 페이지 선차감.
4. **생애주기 타임라인**: heap 생성(create_bestspace) → 첫 INSERT(lazy build) →
   운영(30s sync, add_bestpage 피드백) → shutdown sync → 재시작(rebuild) → heap_reuse/compactdb(재생성).

## B. 개념 퀴즈 (25문)

### 구조
1. L1/L2/L3 각각의 크기(바이트)와, 셋 모두 8바이트여야만 하는 이유는?
2. tier는 몇 단계이고 FS0이 L2/L3 bitmap에 인덱싱되지 않는 이유는?
3. shard가 4800B/64B 정렬인 이유는? atomic_wrapper가 64B인 이유는?
4. allocating bit를 L3 bitmap과 분리한 이유는? (커밋 "split the allocating bit and L3")
5. candidate queue가 lock-free가 아니라 mutex인데도 병목이 아닌 이유 2가지는?
6. shard 수의 기본값/최소/최대는? root class heap만 shard 1개인 이유는?
7. registry 키가 (class_oid, hfid) 쌍이 아니라 HFID 단독인 이유는? class_oid는 어디에 쓰이나?
8. TLS registry 캐시의 크기 상한과 무효화 메커니즘(generation)은?

### 탐색/동시성
9. `needed_size`와 `consume_size`의 차이와 각각의 계산식은? needed가 페이지 용량을 넘으면?
10. L1_find가 페이지를 fix하기 **전**과 **후**에 각각 무엇을 검사하나? (총 4단계)
11. L1_fix가 latch를 0ms도 기다리지 않는(LK_FORCE_ZERO_WAIT) 이유는? CONTENDED를 받은
    호출자는 무엇을 하나?
12. L1 CAS "선차감"(freespace -= consume)의 의미는? 실제 insert가 그보다 작게 쓰면
    누가 언제 보정하나? 반대로 기록값이 실제보다 **작을** 때는? (☜ 함정 질문)
13. 두 스레드가 같은 L1 entry에서 동시에 CAS하면 무슨 일이 일어나나? VPID 비교
    (`VPID_EQ(&vpid, &old_vpid)`)는 왜 필요한가?
14. 모든 shard가 ALLOCATING이면 스레드는 어떻게 대기하나? 왜 보유한 ordered page를
    전부 unfix하고 대기해야 하나? (pgbuf_ordered_callback의 존재 이유)
15. estimates(num_recs, recs_sumlen)는 언제 증가하고 언제 감소하나? DELETE 2000행 직후
    `SHOW HEAP HEADER`의 recs 추정치는?
16. relocation(REC_NEWHOME) 레코드가 num_recs에 계상되지 않는 이유는?

### 피드백/영속화
17. heap_add_bestpage의 유입 지점 3곳과, candidate가 되기 위한 tier 조건은?
18. 30초 sync는 어떤 스레드가 수행하나? find **전에** 하는 이유는? (코드 주석 근거)
19. shutdown sync의 콜스택(3단계)과, crash 시에는 무엇이 유실되는지?
20. shard 페이지 갱신의 recovery index 이름/번호와 로깅 방식(undo? redo?)은?
21. heap_reuse(TRUNCATE 계열)는 bestspace를 어떻게 처리하나?

### 실측/결함 (03/05 문서)
22. 8-커넥션 4000 INSERT에서 shard 분포가 4001:6:1이었던 코드 원인(정확한 두 변수)과,
    shard 1/2가 그나마 쓰인 유일한 계기는?
23. 재시작 직후 vacuum이 회수한 37페이지의 free space 정보가 유실된 정확한 코드 경로는?
    그 결과로 나타난 JIRA 실전 회귀는?(원룡송 코멘트의 증상)
24. 구버전 DB 이미지를 새 바이너리로 열면 왜 위험한가? (TPC-C 사고의 전말)
25. YCSB INSERT 100%와 TPC-C에서 보고된 성능 개선 수치는?

## C. 실습 시나리오 (로컬 검증)

1. **트레이스 재현**: `evidence/bstrace-instrumentation.patch` 적용 → 빌드 →
   `gen_workload.sh 8 500` + `run_multi.sh 8` → find/FOUND의 shard 분포를 직접 집계.
   기대값: shard 0 편중. (개선 구현이라면 균등 분포가 나와야 함)
2. **bloat 재현**: JIRA CBRD-26176 원룡송 코멘트의 repro_clean.sh 실행 →
   delta ≈ 60~80 확인. (수정 빌드 목표: ≤13)
3. **gdb 워크스루**: 비계측 빌드에서 `break cubstorage::bestspace::find` 후
   `csql -S`로 INSERT 1건 — §1의 스택을 자기 손으로 재현하고 frame별로 설명.
4. **rebuild 관찰**: 서버 재시작 후 첫 INSERT에서 `heap_build_bestspace` breakpoint —
   header에서 로드되는 entries/candidates 값을 직접 확인.
5. **SHOW 확인**: `SHOW HEAP HEADER OF <t>`로 estimates/candidates가 30초 sync 전후로
   어떻게 변하는지 관찰.

## D. 최종 관문 — 재작성 시뮬레이션

빈 문서에서 시작해 다음을 작성할 수 있으면 인수인계 완료로 판단한다:
1. `bestspace.hpp`의 public 인터페이스(클래스/메서드 시그니처)를 기억만으로 복원 (±사소한 차이 허용)
2. heap_file.c에 필요한 훅 지점 7곳 열거 (create/insert/delete/undo/stats/reuse/shutdown)
3. 디스크 포맷: header bestspace 블록 필드와 shard 페이지 레이아웃 서술
4. 05 문서의 결함 표를 보지 않고 결함 5개 이상 + 각각의 예방 설계 설명

---
---

## 정답 요약 (스포일러)

**B1** 모두 8B. `std::atomic<T>`가 lock-free이려면 워드 크기여야 하므로(정적 assert로 강제),
64bit CAS 한 번으로 전체 상태를 원자 교체하기 위함. L1=(u16 fs, s16 volid, s32 pageid),
L2/L3=tier 8개×8bit bitmap.
**B2** FS0(1-7%)~FS8(85-100%) 9단계(+FSEND). FS0은 "사실상 가득 참"이라 탐색 대상이
아니므로 bitmap 8칸(FS1~FS8)에만 매핑, 요구 tier가 FS0이면 FS1로 승격하고 정확한 크기
검사는 L1_find의 실측에 맡긴다.
**B3** cache line(64B) false sharing 방지. shard 구성원(allocating+L3+L2×8+L1×64 = 75개
atomic × 64B = 4800B)이 서로 다른 라인에 놓이도록.
**B4** L3 bitmap은 CAS 루프로 자주 재수렴되는데 allocating 상태까지 같은 워드에 있으면
탐색자들이 allocating 확인/설정 때마다 L3 CAS와 충돌한다. 상태의 성격(탐색 힌트 vs
단일 진입 게이트)이 달라 분리.
**B5** ① allocate와 add_bestpage 경로에서만 접근(핫패스인 find에서는 안 씀),
② try_push는 try_to_lock이라 경합 시 그냥 버림(hint이므로 허용).
**B6** 기본 8, 최소 1, 최대 28 (`bestspace_shard_count`). root class heap은 클래스 생성이
드물고 SCH_M lock으로 직렬화되므로 shard가 무의미 + 메모리 절약.
**B7** 같은 heap(HFID)이 곧 하나의 공간 관리 단위이고 class_oid는 파티션/스키마 변경에
따라 재바인딩될 수 있음. class_oid는 L1이 가리키는 페이지가 "아직 그 클래스 소유인지"
검증(stale entry 제거)에 사용.
**B8** TLS_MAX_SIZE=40, LRU. 전역 registry destroy 시 m_generation 증가 → TLS는 조회 때
generation 불일치를 보고 전체 무효화.
**B9** consume = record + slot(4). needed = consume + unfill_space(기본 10%≈1634@16K).
needed > heap_nonheader_page_capacity()면 needed = consume (초대형 레코드는 unfill 무시).
**B10** fix 전: 기록 freespace ≥ needed (아니면 fix 없이 탈락). fix 후: ① PAGE_HEAP 타입,
② class_oid 일치, ③ 실측 free space ≥ needed. 사이사이 stale이면 L1_remove/축소 CAS.
**B11** latch 대기 자체가 기존 병목의 본질이었으므로. 어차피 다른 페이지도 후보로 많다.
CONTENDED를 받으면 같은 L2의 다음 L1 → 다음 L2 → 다음 tier로 진행하고, 전부 경합이면
allocate로 (contended 플래그는 NOT_FOUND와 구별되어 반환됨).
**B12** 선차감은 "이 페이지에 이만큼 넣을 예정"이라는 낙관적 예약 — 이후 같은 페이지로
몰리는 것을 즉시 줄인다. 과대(실제로 덜 씀)면 다음 L1_find의 실측 재검증이나 30s sync가
보정. **과소(실제 free가 더 큼)면 아무도 그 페이지를 fix해 볼 이유가 없어 자가치유
불가** — vacuum-후-재시작 bloat의 근본 원인(03 §7.3).
**B13** 한쪽 CAS만 성공. 실패한 쪽은 그냥 진행(둘 다 이미 페이지 latch를 안 잡았거나
한쪽만 잡음 — freespace 판단은 latch 승자의 실측이 우선). VPID_EQ 비교는 그 사이 allocate가
L1 슬롯을 **다른 페이지로 교체**했을 수 있어, 엉뚱한 페이지의 freespace를 덮어쓰는 것을
막는다.
**B14** pgbuf_ordered_callback으로 보유 ordered page 전부 unfix → yield(20회 이후 10µs
sleep) → 재시도. latch를 쥔 채 기다리면 allocate 중인 스레드(heap header 등 fix 필요)와
latch 순서 역전 deadlock이 나기 때문.
**B15** 증가: find FOUND 시 shard atomic에 (is_newrec, consume-4) 가산, 페이지 할당 시
num_pages 가산. 감소: 런타임 없음 — full-scan(set_estimates: heap_update_statistics,
heap_reuse) 시에만 재설정. DELETE 직후에도 추정 recs는 그대로(실측: 4000 유지).
**B16** 이미 계상된 레코드의 이사(relocation)일 뿐 새 레코드가 아니므로 — 커밋
"do not count relocation record as a new record". 넣으면 recs가 이중 계상됨.
**B17** heap_delete_physical / heap_rv_undo_insert / heap_update_statistics(전체 스캔).
조건: free space tier ≥ FS3(25%).
**B18** 다음 INSERT를 수행하는 스레드가 자기 요청 처리 중에 수행(전용 데몬 없음).
update가 페이지를 unfix할 수 있어서 find로 페이지를 쥔 뒤에는 못 하기 때문 — 코드 주석
"update may unfix the fixed page (best page) so sync … first".
**B19** xboot_shutdown_server → heap_update_all_bestspaces → registry.for_each(
heap_update_bestspace). crash 시 마지막 주기 sync 이후의 L1/candidate/estimates 변화 유실
→ 재시작 rebuild는 stale snapshot 기반(허용된 설계).
**B20** RVHF_UPDATE_BESTSPACE_ENTRIES = 130 (recovery.h). redo-only(log_append_redo_recdes)
— hint라서 undo 불필요.
**B21** 전체 페이지를 걷어 후보를 헤더에 직접 재구성하고(candidates 재적재, shard 수
재기록) registry entry를 destroy → 다음 조회에서 rebuild.
**B22** bestspace::find의 `shard = 0; bias = 0;` 고정 (bestspace.cpp:1361-1362, 커밋
2c7071fd에서 회귀). shard 1/2가 쓰인 유일한 계기는 shard 0(및 1)이 allocating bit에
막혔을 때(alloc/busy → ALLOCATING 반환 → find_from_shards가 다음 shard로).
**B23** vacuum → heap_add_bestpage → `heap_find_bestspace(thread_p, NULL(class_oid), …)`
→ registry miss + class_oid 없음 → rebuild 없이 NULL 반환 → try_push 미도달, 후보 폐기
(heap_file.c:4507-4510). 실전 회귀: DELETE+INSERT 반복 시 heap 페이지가 41→100+로 증가
(repro_clean.sh, 작성자도 vacuum 페이지 재사용 조건 버그로 인정).
**B24** HEAP_HDR_STATS 디스크 레이아웃이 바뀌었는데 compat level은 그대로라, 구 이미지의
작은 header record를 새 구조체로 cast — release에서는 쓰레기 VPID/num_shards를 읽어
"Bad file descriptor"류 I/O 오류·abort 폭증(TPC-C 사고). 작성자 공식 입장은 "DB 재생성
필요". 재작성 시 compat bump 또는 마이그레이션 필수.
**B25** YCSB INSERT 100% 약 +80%, INSERT..SELECT 약 3배, TPC-C(TF 내부, CBRD-26664 병행)
tpmC 54,754 → 59,385 (+8.5%).
