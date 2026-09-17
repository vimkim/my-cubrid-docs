# [CBRD-27089] Destination-owned deferred OOS write — 해설

https://jira.cubrid.org/browse/CBRD-27089 · [PR #7927](https://github.com/CUBRID/cubrid/pull/7927)

> 이 문서는 시간순 감사 기록인 [CBRD-27089-deferred-write_be7c01a_codex.md](CBRD-27089-deferred-write_be7c01a_codex.md) 를 배경 → 문제 → 설계 → 비용 → 검증 → 수용 순서로 재구성한 해설이다. 수치와 증거 링크는 원문과 같으며, 게시 시점별 원본 기록이 필요하면 원문을 본다.

## Background

OOS (Out-of-row Overflow Storage) 는 큰 가변 컬럼 값을 heap record 안에 두지 않고 전용 OOS file 에 저장하는 방식이다. record 가 임계 크기를 넘으면 가장 큰 가변 값부터 OOS 로 옮기고, record 안에는 24 바이트 OOS inline stub (head OOS OID 8B + full length 8B + identity stamp 8B) 만 남긴다. OOS 로 옮겨진 값 하나는 하나 이상의 chunk record 가 이어진 OOS value chain 으로 저장된다.

이 구조에는 heap 단위 소유 불변식이 있다. OOS file 은 heap file 당 최대 하나이고, 그 위치 (OOS VFID) 는 heap header page 가 보관한다. 따라서 record 의 OOS value chain 은 그 record 가 실제로 저장된 heap 의 OOS file 안에 있어야 한다.

읽기 경로는 이 불변식이 깨져도 동작한다. SELECT 는 stub 안의 head OOS OID 로 chain 을 직접 따라가므로, chain 이 엉뚱한 heap 의 OOS file 에 있어도 값은 정확히 나온다. 반면 vacuum 은 죽은 record version 을 치울 때 record 가 저장된 heap 의 header 에서 OOS VFID 를 찾아 chain 을 삭제한다. 소유가 어긋나면 읽기는 멀쩡한 채 vacuum 만 실패한다 — 이 비대칭이 이 결함을 오래 숨긴 이유다.

## Problem

파티션 테이블에서는 record 가 들어갈 heap 후보가 둘 이상이다 (root class 와 child partition 들). 기존 `locator_attribute_info_force` 는 record 를 먼저 직렬화했고, 이 직렬화 단계의 `heap_attrinfo_insert_to_oos` 는 그 시점에 아는 유일한 class 인 root class OID 를 소유자로 OOS value chain 을 기록했다. child partition 을 고르는 `partition_prune_insert` / `partition_prune_update` 는 그 뒤에 실행된다.

```
locator_attribute_info_force
 ├ record transform
 │  └ heap_attrinfo_insert_to_oos(root class)   ★ chain 은 root 의 OOS file 로
 └ partition pruning
    └ record write                              ★ record 는 child heap 으로
```

그 결과 record 와 chain 의 소유 heap 이 갈라진다. SELECT 값 비교로는 잡히지 않고, vacuum 이 child heap header 에서 OOS VFID 를 찾지 못할 때 드러난다. 불변식 위반 시 중단하도록 심어 둔 merge-readiness 계측 (`vacuum_oos_find_vfid_for_heap_record`) 이 있는 빌드는 abort 로 cub_server 가 죽고 (QA 실패), 계측을 빼면 chain 정리를 건너뛰어 저장 공간이 누수된다.

record 크기와 무관하게 컬럼을 항상 OOS 로 보내는 `STORAGE FORCE_OUTLINE` 옵션을 쓰면 64 바이트 값으로도 재현된다. 재현 스크립트와 기대/실제 결과는 JIRA 의 Repro 절에 있다.

## First approach and why it was replaced

첫 수정 (PR #7600) 은 two-pass 였다. probe transform 이 OOS demote 를 억제한 fully-inline image 로 partition 을 먼저 결정하고, final transform 이 선택된 child 를 소유자로 chain 을 기록한다. 이 방식은 record 를 두 번 변환해야 하고, chain 을 만들 수 있는 producer 경로마다 suppression 을 개별로 끼워야 했다. 실제로 FORCE_OUTLINE 경로가 record-size gate 앞에서 OOS 선택을 먼저 확정해 suppression 검사에 도달하지 않았고, probe 단계에서 root 에 chain 을 쓰는 구멍이 남았다.

그래서 접근을 뒤집었다. 값을 억제하는 대신 **한 번만 준비해 소유하고, 목적지가 정해진 뒤에만 기록한다** (destination-owned deferred write). PR #7927 이 이 재설계이고, PR #7600 과 그 브랜치는 이력 보존을 위해 유지한다.

## Design — prepare, route, finalize

```
producer (INSERT / UPDATE / 파티션 이동 / loader / 재분배 / 복제 ...)
  → heap_prepared_row     모든 컬럼의 canonical bytes 를 한 번 직렬화해 소유
  → partition adapter     준비된 값으로 기존 partition expression 평가
  → locator               destination heap 선택
  → shared finalizer      destination heap 의 OOS file 에 value chain 기록,
                          24B stub 을 채워 heap record 완성
  → 기존 heap / index / replication 소비자
```

**준비 (prepare)** — `src/storage/heap_prepared_row.hpp` 가 movable/non-copyable owner 의 인터페이스이고, 구현은 `src/storage/heap_file.c` 에 있다. OOS 후보만이 아니라 일반 컬럼까지 소유하므로 입력 `DB_VALUE` 가 정리된 뒤에도 행이 유효하다. OOS 값을 전부 inline 으로 넣은 임시 행은 만들지 않고, OOS payload 를 finalization 용으로 다시 복사하지도 않는다. column/plan 저장소는 크기를 먼저 확정해 finalization 중 이동하지 않으며, allocation 실패는 CUBRID 오류 코드로 반환한다. owner 소멸자는 메모리만 해제한다 — 이미 기록된 내용의 취소는 기존 transaction/system operation 과 명시적 publication 정리가 담당한다.

**경로 결정 (route)** — `src/query/partition.c` 의 adapter 가 raw 값이나 미완성 stub 대신 준비된 값을 읽어 기존 partition expression 을 평가한다. 타입 직렬화, default 값, unassigned UPDATE, increment, 외부 LOB copy 의미는 baseline 그대로다.

**기록 (finalize)** — 목적지가 정해진 뒤에야 chain 이 생기므로 잘못된 소유자가 생길 시점 자체가 없다. REPLACE 와 `INSERT ... ON DUPLICATE KEY UPDATE` 의 중복 키 탐색은 준비된 key 만 읽고 chain 을 기록하지 않으므로, 삽입되지 않는 탐색용 image 가 orphan chain 을 남기지도 않는다. 쓰기가 실패하면 행과 chain 이 같은 rollback 범위에서 함께 취소된다.

**identity stamp 연동** — feat/oos 에 먼저 들어간 24B stub 형식 (CBRD-26950 의 page-LSA identity stamp) 과 merge 하면서 연결 작업이 하나 필요했다. merge 직후 50KB prepared-owner readback 이 오류 -1384 로 실패했는데, 준비된 request 가 안정적인 plan storage 에 head identity stamp 를 받고 finalizer 가 OID·length 뒤에 packed stamp 를 기록하도록 연결해 해결했다. replica 는 incoming code 의 replica-local stamp fixup 을 그대로 쓴다.

**바꾸지 않은 것** — 저장/통신 format, demotion 정책 (largest-first, four-record target), SQL 의미는 그대로다. OOS 와 ordinary bigone 이 동시에 필요한 행은 기존 정책대로 OOS 기록 전에 거절한다.

### 적용한 producer 경로

chain 을 만들 수 있는 모든 쓰기 경로가 같은 준비 → 기록 계약을 따르도록 감사했다:

| 경로 | 적용 방식 |
|---|---|
| SQL INSERT / UPDATE / 파티션 이동 | `locator_attribute_info_force` 에서 준비 → routing → finalize; 이동은 같은 owner 를 목적지 INSERT 로 전달 |
| REPLACE / duplicate-key UPDATE | 중복 키 probe 는 준비된 key 만 읽음 — OOS 기록 없음 |
| Raw client rows (copy area) | `locator_prepare_client_row` 가 SQL 재평가 없이 준비 형식으로 변환 |
| 파티션 재분배 | 속성별 OOS Resolve 후 목적지에서 새 chain 생성, 원본 MVCC header 보존 |
| Server / bulk / HA loader | 큐마다 owner 보유, retained payload 로 flush 판정; HA 는 행별 system operation 안에서 finalize 와 publication |
| Replica | 완료된 record 의 기존 OID fixup; OOS items 와 heap row 가 한 rollback 범위, 무시 가능한 오류 뒤에도 잔류 chain 없음 |
| Serial / catalog / 내부 경로 | complete-record 경로 유지; catalog bootstrap 은 preparation 우회 (Verification 참고) |

UPDATE 의 OOS replication producer 위치는 옮기지 않았다. 파티션 이동은 destination INSERT 가 publication 을 소비한 뒤 source DELETE 가 key-based delete 만 기록한다.

## Cost — payload 를 더 오래 들고 있는 값

기록을 목적지 결정까지 미루므로, 특히 loader 가 canonical payload 를 baseline 보다 오래 보유한다. 이 비용은 측정해서 공개하고 수용했으며, 메모리 개선으로 포장하지 않는다.

동일 workload 3회 반복 측정 (KiB, server peak = 쓰기 완료 직후 `VmHWM`):

- **Loader 경로**: be7c01a 시점 median 차이 +7,776 (mixed 600행) / +8,316 (1,000×50KB). merge 후 512b361 시점 parent 대비 growth 차이 +7,084 / +7,596 — 방향과 크기가 retained payload 비용과 일치한다.
- **SQL 경로**: -24 / -640 등 startup 변동 범위 안 — 의미 있는 회귀로 판정하지 않는다 (SQL 은 한 번에 한 행만 준비를 보유한다).
- **직접 계수**: 50KB 값의 owner 는 50,392B 를 보유하고, 64행 × 50KB 큐는 약 3.2MB (3,225,600B) 를 보유한다. process RSS 는 allocator·buffer pool 잔류를 포함하므로 live payload 의 정확한 계수로 읽지 않는다.

loader 의 기존 per-worker 8MiB flush 기준에 canonical payload 와 owner capacity 를 계산해 넣었다. 이 기준은 process 전체 RSS cap 이 아니며, 새 허용 threshold 를 만들거나 지원 행/키 범위를 줄이지 않았다. 원본 수치와 실행 파일 해시: [be7c01a baseline](deferred-write-be7c01a-evidence/memory-baseline.json) / [candidate](deferred-write-be7c01a-evidence/memory-changed.json), [512b361 parent](deferred-write-512b361-evidence/memory-38093ea.json) / [candidate](deferred-write-512b361-evidence/memory-identity-merged.json).

## Verification

로컬 검증 (feat/oos merge 후 source `512b361a7`, Linux x86_64, GCC Debug):

| 검증 | 결과 | 증거 |
|---|---|---|
| Configured CTest | 35/35 (identity, no-logging, crash recovery 포함) | [full-tests-final.log](deferred-write-512b361-evidence/full-tests-final.log) |
| 실제 server loader | mixed 600행, 9MiB 행, 실패 rollback, concurrent load 성공 | [loader.log](deferred-write-512b361-evidence/loader.log) |
| 실제 source/standby 복제 | 값·이동·publication 순서·양쪽 실패 cleanup 성공 | [replication.log](deferred-write-512b361-evidence/replication.log) |
| MVCC + SIGKILL/재시작 복구 | snapshot, committed redo, uncommitted undo, multi-chunk, serial 성공 | [transactions-barrier.log](deferred-write-512b361-evidence/transactions-barrier.log) |
| Catalog bootstrap | 새 4KB DB utility 와 기존 CTP case 1/1 성공 | [bootstrap.log](deferred-write-512b361-evidence/bootstrap.log), [ctp-feedback.log](deferred-write-512b361-evidence/ctp-feedback.log) |
| Scoped Valgrind 3.24.0 | invalid access 0, lost 0B (owner lifetime/failure 테스트 3개) | [valgrind.log](deferred-write-512b361-evidence/valgrind.log) |

원격 CI (같은 source):

- GitHub static checks 5/5, release/debug/download build 성공.
- medium 3/975 · SQL 2/17463 · shell 20/3277 실패 (error/unknown 0). 25건 전수 분류 결과 **24건은 최신 parent `38093ea85` 에서 독립 재현되는 baseline 실패**, 1건은 잘못된 partition 입력에 대한 의도된 거절이다. 이 PR 이 도입한 실패는 없다.
- 상세: [CI 분석 보고서](ci_analysis_report_512b361_codex.md), [25건 분류](deferred-write-512b361-acceptance/classification.json).

merge 과정에서 필요했던 적응은 세 가지다. (1) catalog bootstrap 중에는 catalog OID cache 가 없어 `_db_authorization` 이 ordinary row 로 분류되므로, catalog 활성화 전에는 complete-record preparation 과 오류 cleanup 을 우회했다 (`6acfbb823`). (2) 24B stub 도입으로 20자 key 가 eligibility 하한 (24B 초과) 아래로 내려가 더 이상 outline 되지 않아, duplicate-probe fixture 의 key 를 26자로 늘렸다 — expected OOS count 를 낮춰 통과시키지 않았다. (3) recovery runner 의 재시작이 killed process 종료와 master 등록 제거 사이 race 로 실패해, 등록 제거를 bounded polling 으로 기다린 뒤 기존 one-shot restart 를 실행하도록 고쳤다.

재현 방법: [verification guide](https://github.com/vimkim/cubrid/blob/be7c01a6d2d05d461cb1e5b6e0127c15ffb1950b/unit_tests/oos/scripts/README.verification.md) 를 따라 소스를 고정해 빌드·설치한 뒤 `ctest --test-dir <build-directory> --output-on-failure` 를 실행한다. 실제 서버 runner 는 각각 별도 Linux network namespace 와 fresh DB 를 사용한다.

## Acceptance and limits

2026-09-15 에 남아 있던 두 검증 항목 (V21-CI: 원격 CI 수집·분류, V21-ACCEPT: 종합 수용 판단) 을 완료하고, destination-owned deferred-write 교체를 해당 범위에서 수용했다. 검증 source 는 `512b361a7`, 비교 parent 는 `38093ea85` 다.

이 결정이 보증하지 않는 것은 다음과 같다:

- **CI 전체 green 이 아니다.** 남은 실패는 전부 parent 재현 baseline 이거나 의도된 거절이다.
- **baseline 자체의 결함은 범위 밖이다.** 기존 vacuum 계열 결함과 WAL/미초기화 값 Valgrind 진단은 별도 ticket 소관이다.
- **subsystem 전체 보증이 아니다.** vacuum convergence, no-logging crash durability, multi-node heartbeat failover, exhaustive concurrency, release throughput 은 이 증거로 증명하지 않았다.
- **Valgrind 는 scoped 결과다.** `--undef-value-errors=no` 조건이므로 engine 전체의 undefined-value cleanliness 를 뜻하지 않는다.
- **최신 OOS 규범의 나머지 항목은 별도 작업이다.** UPDATE chain reuse (CBRD-27230), vacuum slot-reuse 후속 (CBRD-26950 계열) 등을 이 PR 이 해결했다고 설명하지 않는다.

## References

| 항목 | 식별자 |
|---|---|
| 결함 baseline | `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` |
| 최초 게시 source | `be7c01a6d2d05d461cb1e5b6e0127c15ffb1950b` |
| merge 후 검증 source | `512b361a7a34a4857cd8ad91c496c7e0e94c0769` |
| 비교 parent | `38093ea859a8a08e20405b72b0cb395205bedb2f` |
| 현재 PR head | `bffe13be29ccb8f11d1789cd002da9e03315fd93` (CI acceptance 증거 기록) |
| 보존한 PR #7600 head | `479cd960ec04196c92bf9789b1fc340af9046c2c` |

- 원본 감사 기록 (시간순, 전체 증거 표): [CBRD-27089-deferred-write_be7c01a_codex.md](CBRD-27089-deferred-write_be7c01a_codex.md)
- 증거 디렉터리: [be7c01a](deferred-write-be7c01a-evidence/), [512b361](deferred-write-512b361-evidence/), [acceptance](deferred-write-512b361-acceptance/)
- PR: [#7927](https://github.com/CUBRID/cubrid/pull/7927) (현행), [#7600](https://github.com/CUBRID/cubrid/pull/7600) (보존)
- 관련 ticket: CBRD-26835 (parent), CBRD-26950 (identity stamp), CBRD-27230 / CBRD-27237 (범위 밖 후속)
