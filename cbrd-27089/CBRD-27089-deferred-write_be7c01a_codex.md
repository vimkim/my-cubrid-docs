# [CBRD-27089] Destination-owned deferred OOS writes

https://jira.cubrid.org/browse/CBRD-27089

## Purpose

- AS-IS: 목적지 파티션을 고르기 전에 OOS value chain (큰 컬럼 값을 저장하는 연결된 레코드)을 root heap 에 기록한다. 행은 child heap 에 기록되어, SELECT 값은 맞아도 물리적 소유 heap 이 다를 수 있다.
- TO-BE: canonical serialized value (저장 형식으로 정규화한 값)를 한 번 준비하여 소유하고, 그 값으로 목적지를 선택한 뒤 destination heap 의 OOS file 에 기록한다.

PR7600의 early-key/two-pass 접근을 대체하는 별도 draft다. 기존 PR과 브랜치는 보존한다. 현재 JIRA 설명은 이전 구현의 설명이므로 이번 구현 계약은 사용자 승인 destination-owned 설계다. JIRA 설명을 수정하거나 이전 PR을 닫지 않았다.

| 구분 | 고정 식별자 |
|---|---|
| 비교 baseline / 게시 시점 target | `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` |
| 게시 source | `be7c01a6d2d05d461cb1e5b6e0127c15ffb1950b` |
| Source / target | `vimkim:feat/oos-deferred-write` → `CUBRID/CUBRID:feat/oos` |
| 기존 PR7600 head | `479cd960ec04196c92bf9789b1fc340af9046c2c` |
| 검증 환경 | Linux x86_64, GCC 11.5.0, Debug, `UNIT_TEST_OOS=ON` |

이전 단계에서 보존한 baseline의 64B FORCE_OUTLINE 재현은 값 비교가 1이지만 root OOS record 1, child 0이었다. 교체 테스트는 값 비교와 목적지별 live OOS chunk 수를 함께 검증한다. SELECT 성공만으로 ownership 수정을 판정하지 않는다.

## Implementation

### 준비와 목적지 기록

```text
ordinary producer
  → heap_prepared_row: canonical attribute bytes 소유
  → partition adapter: 준비된 값으로 기존 partition expression 평가
  → locator: destination 선택
  → shared finalizer: destination OOS file 에 값 기록 + heap record 완성
  → 기존 heap/index/replication 소비자
```

`src/storage/heap_prepared_row.hpp` 는 movable/non-copyable owner의 인터페이스다. 구현은 `src/storage/heap_file.c` 에 있다. 일반 컬럼도 소유하므로 입력 DB_VALUE 정리 이후에도 행이 유효하다. OOS 값을 모두 inline으로 넣은 임시 행은 만들지 않는다. 최종 compact record와 컬럼별 serialized bytes를 보유하며, OOS payload는 finalization용으로 다시 복사하지 않는다.

column/plan 저장소를 먼저 크기 확정한 뒤 batch request가 payload와 OID 결과 슬롯을 빌린다. finalization 중 이 저장소는 이동하지 않는다. allocation 오류는 CUBRID 오류 코드로 반환한다. owner 소멸자는 메모리만 해제하고, 실제 기록의 취소는 기존 transaction/system operation과 명시적 publication 정리가 담당한다.

`src/query/partition.c` 의 adapter는 raw assigned value나 미완성 stub을 읽지 않고 준비된 값을 읽는다. 기존 타입 직렬화, partition expression/comparison, default, unassigned UPDATE, increment와 외부 LOB copy 의미를 보존한다. 한 write attempt의 buffer 처리 때문에 이 효과를 반복하지 않는다. 중복 탐색과 실제 쓰기는 각각 독립된 준비다.

final layout은 baseline의 demotion/storage 정책, variable offsets, alignment와 최대 MVCC header 증가분을 반영한다. OOS와 ordinary bigone이 동시에 필요한 행은 OOS 기록 전에 거절한다. OOS가 없는 ordinary overflow와 유효한 compact OOS 행은 허용한다. 이 PR은 저장/통신 형식을 변경하지 않는다.

### Producer audit

| 경로 | 적용 위치와 보존 계약 | 검증 경계 |
|---|---|---|
| SQL INSERT | `locator_attribute_info_force` 준비 → `locator_insert_force` routing/finalize → heap insert | SQL 값·partition ownership·default·LOB·실패 |
| UPDATE / movement | 목적지 선택 뒤 index/replication 앞에서 finalize; 이동 시 같은 owner 전달 | 같은/다른 partition, key domain, unassigned value, FK, rollback |
| REPLACE / duplicate-key UPDATE | `query_executor.c` 의 probe가 준비된 key만 읽음; OOS 기록 없음 | 두 probe, multiple/composite unique key, LOB, 실패 이후 쓰기 |
| Raw client rows | `locator_prepare_client_row` / `prepare_serialized`; SQL expression 재평가 없이 adaptation | copy-area insert/update/multi-update, 이동·실패 |
| Redistribution | 속성별 OOS Resolve 후 목적지에서 새 chain 생성; 원본 MVCC header 보존 | multi-chunk ownership·원본 수명·실패 |
| Server loader | 큐마다 owner 보유; retained payload로 flush 판정 | 입력 정리, mixed batch, 9MiB 행, filtered/unfiltered error, concurrent loader |
| Bulk loader | nonpartitioned/non-HA에서 OOS finalization을 bulk heap page latch 전에 완료 | 실제 loader와 queue rollback |
| HA loader | row system operation 안에서 finalize와 publication; 행별 로그 순서 유지 | source/standby의 모든 값과 commit barrier 비교 |
| Replica | 완료된 record의 기존 OID fixup; OOS items와 heap row가 하나의 rollback 범위 | 정상 복제·truncated group·무시한 중복 오류 뒤 live chunk parity |
| Serial / address / internal | complete-record 및 명시적 bypass 유지; HAS_OOS 부재만으로 pending 판정 안 함 | serial 재시작·reservation·catalog 테스트 |
| MVCC assignment helper | complete-record 호환 함수 유지; ordinary UPDATE는 old record를 전달해 이 분기를 우회 | caller audit와 SQL 회귀 |
| Standalone loader | baseline의 workspace 경로와 no-logging readback 유지 | OOS 활성화는 별도 CBRD-27424 범위 |

UPDATE의 OOS replication producer를 heap operation으로 옮기지 않았다. 이동의 destination INSERT가 publication을 소비한 후 source DELETE는 key-based delete만 기록한다. Replica의 무시 가능한 오류도 앞선 OOS allocations를 함께 취소하여 다음 행에 남지 않도록 한다.

### Final review repairs

전체 baseline→source diff를 독립된 Standards·Spec 축으로 검토했다. Standards는 새 C++ member 호출의 GNU indent 보호 구간 누락과 두 runner의 runtime 생성 중복을 지적했다. 정확한 `INDENT-OFF/ON` 구간을 추가하고 `LoaderFixture.isolate_runtime` 으로 공통화했다. 재검토에서 두 지적은 해소되었고 Spec의 actionable code finding은 0이다. 동작 변경 없는 보호 주석 추가 외에 엔진 코드를 재설계하지 않았다. 불필요한 indentation-only 변화는 없다.

## Remarks

### Test Plan

최종 결과와 증거 링크는 아래 실행 결과 표에 기록한다. 전체 configured CTest는 CTP SQL/medium/shell 전체와 다른 범위다. `UNIT_TESTS=OFF`이며 OOS, page-buffer, slotted-page의 개별 설정을 사용하는 구성이다. 실행 파일·라이브러리·변경 파일 해시는 [provenance](deferred-write-be7c01a-evidence/provenance.json)에 고정한다.

| 실행 | 결과 | 공개 증거 |
|---|---|---|
| 최종 build/install + configured CTest | 27/27, 136.05초, exit 0 | [전체 로그](deferred-write-be7c01a-evidence/full-suite.log) |
| 실제 server loader | partition ownership, 600 mixed rows, 9MiB legal row, filtered/unfiltered 실패, concurrent 600행, 기존 SA no-logging readback 통과 | [요약](deferred-write-be7c01a-evidence/loader.log), [SQL/config 출력](deferred-write-be7c01a-evidence/loader-fixture-1.json) |
| 실제 source/standby 복제 | INSERT, UPDATE 직후 값, movement, OOS-to-inline, DELETE, HA loader, source/replica 실패 rollback 통과 | [요약](deferred-write-be7c01a-evidence/ha.log), [source](deferred-write-be7c01a-evidence/ha-fixture-1.json), [replica](deferred-write-be7c01a-evidence/ha-fixture-2.json) |
| 실제 server MVCC + SIGKILL/restart | old snapshot, committed redo, uncommitted INSERT/UPDATE/movement undo, multi-chunk ownership, serial persistence 통과 | [요약](deferred-write-be7c01a-evidence/transactions.log), [SQL/config/recovery 출력](deferred-write-be7c01a-evidence/transactions-fixture-1.json) |
| scoped Valgrind 3.24.0 | owner move·loader lifetime·allocation/storage 실패 3개 테스트 통과; invalid access 0, definitely/indirectly/possibly lost 0B | [로그](deferred-write-be7c01a-evidence/valgrind.log), [명령·값·설정](deferred-write-be7c01a-evidence/valgrind-fixture-1.json) |
| Standards / Spec review | Standards 2개 해결, 남은 0; Spec 0 | [Standards](deferred-write-be7c01a-evidence/standards-review.md), [Spec](deferred-write-be7c01a-evidence/spec-review.md) |
| Native format / Python syntax | 변경 C/C++ 파일을 복사본에서 GNU indent/astyle 검사하여 차이 없음; runner AST parse와 diff check 통과 | 최종 commit hook과 로컬 검사; 원격 CI 결과와 구분 |

게시 commit의 소스는 빌드 전 파일과 해시가 일치한다. 실제 서버 검증 뒤 최종 build/install을 다시 했고 실행 파일·라이브러리 해시가 모두 같았다. 최종 전체 테스트와 메모리 측정 이후에도 같은 해시인지 확인했다. 이전 ticket18/19/20의 pass를 최종 실행인 것처럼 재사용하지 않았다.

재현은 [verification guide](https://github.com/vimkim/cubrid/blob/be7c01a6d2d05d461cb1e5b6e0127c15ffb1950b/unit_tests/oos/scripts/README.verification.md)와 그 문서가 연결하는 loader/replication/transactions/memory runner를 사용한다. 소스를 고정하여 빌드·설치한 뒤 `ctest --test-dir <build-directory> --output-on-failure` 를 실행한다. 실제 서버 runner는 각각 별도 Linux network namespace, registry, runtime과 fresh DB를 사용한다. 각 runner의 full-value·ownership·barrier assertion 성공과 exit 0을 함께 확인한다.

### Resource measurements

동일한 GCC Debug 구성, 64MiB data buffer, 16MiB log buffer, loader worker 4개, 32MiB string limit을 사용한다. 각 표 항목은 fresh nonpartitioned DB에서 uncompressed VARBIT workload를 **3회** 실행한 결과다. SQL은 단일 INSERT SELECT transaction, loader는 10,240행 commit 설정이다. write 뒤 완전한 값과 row count도 검사한다.

server peak는 write 완료 직후, readback 전에 읽은 Linux `VmHWM` 이다. client peak는 GNU time maxrss다. 별도 프로세스의 peak를 동시 합계로 더하지 않는다. startup·buffer pool·staging·allocator까지 포함한 process RSS이고 live preparation의 직접 계수가 아니다. OS page cache와 helper process는 제외한다. timing은 병행한 다른 작업의 영향을 받을 수 있으므로 throughput 주장은 하지 않는다.

| workload | baseline server peak KiB (3회) | candidate server peak KiB (3회) | median 차이 KiB | client median baseline / candidate KiB |
|---|---|---|---:|---:|
| SQL 10,000 × 32B | 350392, 350708, 350716 | 351360, 350684, 350632 | -24 | 19,200 / 19,200 |
| SQL 1,000 × 50,000B | 394240, 392960, 391680 | 393600, 392320, 390400 | -640 | 19,840 / 18,560 |
| Loader 600 mixed | 477280, 478136, 477432 | 485420, 484536, 485208 | +7,776 | 59,876 / 58,868 |
| Loader 1,000 × 50,000B | 663752, 663736, 662444 | 671452, 672052, 672096 | +8,316 | 213,484 / 213,484 |

원본 수치와 실행 파일 해시: [baseline](deferred-write-be7c01a-evidence/memory-baseline.json), [최종 candidate](deferred-write-be7c01a-evidence/memory-changed.json). baseline 설치는 기존 증거의 해시와 일치함을 확인했고 두 설치 모두 측정 중 해시 변경이 없었다. 각 JSON은 workload, repetition, write 전 RSS/HWM, write 후 HWM과 client peak를 보존한다.

공개 accounting API의 현재 리비전 관찰은 다음과 같다. owner move-assignment, 입력 값 파괴, finalization 이후 full-value readback까지 검증했다. finalization 전후 retained bytes는 같다.

| payload bytes | owner retained bytes | final record bytes |
|---:|---:|---:|
| 32 | 408 | 68 |
| 4,000 | 8,344 | 4,036 |
| 50,000 | 50,352 | 44 |

64 × 50,000B 큐는 owner container capacity를 포함해 3,223,040B를 보유한다. 4,000B inline 값은 canonical buffer와 최종 record 양쪽에 존재한다. 이는 OOS payload의 finalization 전용 복사와 다르다. `retained_bytes` 는 요청한 allocation capacity를 합산하며 malloc bookkeeping은 제외한다.

최종 SQL server median 차이는 small -24KiB, large -640KiB다. large SQL은 한 번에 한 행의 50,352B 준비를 보유하며 candidate의 세 번 peak 범위는 390,400–393,600KiB다. 이전 ticket20도 390,400–394,240KiB 변동과 640–1,280KiB startup 변동을 기록했다. 따라서 이번 process peak만으로 정확한 준비 메모리 증가량이나 반복 가능한 SQL memory regression을 분리했다고 주장하지 않는다.

loader server median은 mixed **+7,776KiB**, large **+8,316KiB**다. 이전 ticket20의 +7,092KiB/+8,408KiB와 같은 방향의 증가이며, 기준 변경 없이 retained payload의 lifetime과 직접 accounting을 조사했다. allocator와 buffer pool 잔류가 있어 RSS의 모든 KiB를 live queue와 정확히 일치시킬 수는 없다. row별 payload 보유, stable borrowed request, flush accounting, scoped cleanup 통과와 oversized legal-row 통과를 근거로 이 비용을 공개하며, 최종 acceptance는 아래 열린 검증과 함께 판단한다.

loader는 OOS 기록을 뒤로 미루기 때문에 baseline보다 payload를 오래 보유한다. 기존 8MiB **per-worker** flush 기준에 canonical payload와 owner capacity를 계산한다. flush 중 현재 준비 행, 입력 staging, bulk metadata, allocator 잔류와 하나의 oversized legal row는 별도다. 따라서 이 기준은 process RSS cap이나 전체 동시 worker의 peak 상한이 아니다. 이번 비용은 명시적으로 공개하는 deferred lifetime의 비용이며 메모리 개선으로 표현하지 않는다. 수치 허용 비율을 새로 만들거나 지원 행/키 범위를 줄이지 않았다.

### Evidence boundaries and remaining work

- **Baseline에서 재현한 결함:** `f4299ac0c` 의 잘못된 root ownership은 원래 이슈다. ticket19에서 보존한 별도의 unsuppressed Valgrind baseline 실행은 `heap_init_get_context` 와 WAL append/compression 계열 미초기화 값 진단을 재현했다(153,963 errors / 241 contexts, exit 99). 두 workload의 모든 진단을 개별 귀속했다고 주장하지 않는다.
- **현재 scoped memory pass:** `--undef-value-errors=no` 조건으로 invalid access와 lost bytes를 검증한다. 이는 engine 전체가 Valgrind-clean이라는 뜻이 아니다. baseline unsuppressed 로그와 current scoped 결과를 분리하여 보관한다.
- **별도 OOS conformance gaps:** pinned baseline의 16B stub과 기존 demotion 정책을 유지한다. 최신 규범의 24B identity stamp, four-record physical target, UPDATE chain reuse, vacuum 변경을 이 PR에서 구현한 것으로 설명하지 않는다. CBRD-26950·CBRD-27230/27237 등 별도 작업의 해결을 주장하지 않는다.
- **검증 범위:** recovery fixture는 vacuum을 끈 logged-write 검증이다. vacuum reclaim, no-logging durability, multi-node heartbeat failover, exhaustive concurrency, release throughput은 이 결과로 증명하지 않는다. 기존 vacuum 결함은 이 세션에서 재현하지 않았으므로 현재 재현한 baseline 실패로 집계하지 않는다.
- **도입된 실패:** 이번 최종 리비전의 완료된 로컬 검증에서 남은 도입 실패는 없다. 원격 회귀는 아직 확인하지 않았다. 이전 구현 단계에서 발견한 replication DELETE publication과 replica 오류 후 OOS 잔류는 해당 구현 커밋에서 수정했고, 최종 HA 실행이 두 경계를 다시 검증했다.
- **실패 이력:** 첫 full-suite 명령은 외부 fixture가 실행 파일을 사용 중이어서 install이 exit 75로 거절되어 CTest를 시작하지 못했다. fixture 완료 후 순차 재실행했다. 프로세스를 강제 종료하거나 검사 결과를 pass로 바꾸지 않았다. 이 실패는 엔진 회귀가 아니다.

다음 항목이 남아 있어 **verified replacement / merge-ready 완료를 선언하지 않는다**. 로컬 parent spec/map과 work item #117도 열린 상태로 유지한다. 담당은 PR 작성자이며, 아래 체크박스를 증거와 함께 갱신한 뒤 전체 완료를 판단한다.

- [ ] **V21-CI:** 게시 source SHA의 GitHub 정적/스타일 체크 결과와 CTP SQL·medium·shell 결과를 수집한다. 선행 조건은 새 draft에 대한 CI 실행 환경/작업이다. 성공 조건은 같은 source SHA의 완료된 job URL, 실패 목록과 baseline/introduced 분류, 도입된 실패의 수정·재검증이다. 현재 원격 테스트 pass는 없다.
- [ ] **V21-ACCEPT:** V21-CI 결과와 이 문서의 producer/resource matrix를 함께 검토하고 parent acceptance를 갱신한다. baseline 문제와 기능 범위 밖 검증을 성공으로 간주하거나 이 checklist에서 조용히 삭제하지 않는다.

기존 PR7600은 draft/open과 기존 head를 유지한다. CCI generated changes와 private database는 source/docs commit에 포함하지 않는다. 공개 evidence는 fixture 경로를 상대 식별자로 치환한 SQL/config/text/JSON만 포함하며 DB volume이나 credentials를 포함하지 않는다. manifest는 원본 및 게시본 SHA-256을 함께 보존한다.
