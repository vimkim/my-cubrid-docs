# [CBRD-27089] Keep OOS value chains with the pruned partition heap

- JIRA: https://jira.cubrid.org/browse/CBRD-27089
- PR: https://github.com/CUBRID/cubrid/pull/7600
- Base: `origin/feat/oos` at `2940b1cfb`
- Source: `b871ea386d2c5419b7abae07dda58b9b7f36377a`
- Previous design report: [2ed0e60](CBRD-27089-oos-chains-follow-pruned-partition_2ed0e60_claude.md)
- Previous blocking review: [ee2cb7b](PR-7600-report_ee2cb7b_claude.md)

## Outcome

파티션 레코드가 참조하는 OOS value chain 은 이제 그 레코드가 실제로 저장되는 파티션 heap 의 OOS file 에 기록된다. 루트 클래스에는 chain 을 만들지 않는다. 이전 리뷰의 blocking finding 이었던 `STORAGE FORCE_OUTLINE` suppression 우회도 회귀 테스트와 함께 해결했다.

| 관찰 대상 | 수정 전 | 수정 후 |
|---|---:|---:|
| 루트 `t_oos_show_part` OOS record | 1 | 0 |
| 선택된 파티션 `p0` OOS record | 0 | 1 |
| 비선택 파티션 `p1` OOS record | 0 | 0 |
| 논리 값 비교 | 정상 | 정상 |

SELECT 가 수정 전에도 정상인 이유는 inline stub 의 head OOS OID 가 절대 물리 위치를 가리키기 때문이다. 문제는 vacuum 과 file lifecycle 이 현재 heap header 의 OOS VFID 를 사용한다는 데 있었다.

## Root Cause

기존 쓰기 순서는 OOS demotion 이 파티션 pruning 보다 빨랐다.

```text
locator_attribute_info_force
 ├ record transform
 │  └ heap_attrinfo_insert_to_oos(attr_info->class_oid)
 │     └ root heap 의 OOS file 에 value chain 기록
 └ partition_prune_insert / partition_prune_update
    └ 최종 record 는 child partition heap 에 저장
```

그 결과 heap record 의 `HAS_OOS` flag 와 inline stub 은 child partition 에 존재하지만, chain 과 OOS VFID 는 root heap 에 존재했다. vacuum 이 child heap 에서 VFID 를 찾지 못하면 merge-readiness invariant 계측이 abort 했다.

## Implementation

### 파티션 write 의 two-pass transform

`d9f59cb3a` 는 partitioned INSERT/UPDATE 를 다음 순서로 바꾼다.

```text
1. probe transform
   ├ OOS demotion 억제
   └ fully-inline image 로 목적 partition 결정
2. final transform
   ├ pruned class OID 를 OOS owner 로 전달
   └ 선택된 partition heap 의 OOS file 에 chain 기록
3. 기존 locator insert/update 경로로 최종 record 저장
```

`INCR()` / `DECR()` 반영과 LOB copy 는 두 pass 전체에서 한 번만 수행된다. 비파티션 record 와 OOS demotion 이 필요 없는 partition record 는 기존 single-pass 경로를 유지한다.

REPLACE 및 `INSERT ... ON DUPLICATE KEY UPDATE` 의 중복 key probe 도 OOS-suppressed transform 을 사용한다. 삽입되지 않는 임시 image 가 orphan chain 을 만드는 것을 막는다.

### FORCE_OUTLINE suppression

이전 리뷰는 `heap_attrinfo_determine_disk_layout` 의 FORCE_OUTLINE loop 가 suppression mode 를 무시한다고 지적했다. 작은 `FORCE_OUTLINE` value 는 PG-style four-record heap target 아래에서도 강제로 demote 되므로, 일반 size-gate 쪽 suppression 검사만으로는 잡히지 않았다.

`b871ea386` 에서는 FORCE_OUTLINE candidate 를 만났을 때 suppression mode 라면:

1. `would_demote_oos = true` 로 final transform 필요성을 보고한다.
2. `oos_plan.selected` 와 `has_oos` 는 설정하지 않는다.
3. probe image 에 inline value 를 유지하고 OOS value chain 을 쓰지 않는다.

따라서 pruning 이후 final transform 이 반드시 실행되고, chain owner 가 pruned partition 으로 결정된다.

## Regression Test

`unit_tests/oos/sql/test_oos_sql_show.cpp` 의 `PartitionedForceOutlineStoresOosInPrunedHeap` 는 public SQL surface 만 사용한다.

```sql
CREATE TABLE t_oos_show_part (
  id INT,
  data_col BIT VARYING STORAGE FORCE_OUTLINE
)
PARTITION BY RANGE (id) (
  PARTITION p0 VALUES LESS THAN (10),
  PARTITION p1 VALUES LESS THAN MAXVALUE
);

INSERT INTO t_oos_show_part VALUES (1, REPEAT(X'EE', 64));
SHOW ALL HEAP OOS OF t_oos_show_part;
```

`BIT VARYING` 을 사용해 문자열 압축에 따른 disk-size 변동을 피한다. 64-byte value 는 일반 record-size gate 아래지만 FORCE_OUTLINE 정책으로 OOS-backed 가 되어, suppression 우회를 직접 구별한다.

### Red

수정 전에는 다음 assertion 이 실패했다.

```text
root: has_oos=1, oos_num_recs=1
p0:   has_oos=0, oos_num_recs=0
```

### Green

수정 후에는 logical value equality 와 소유 관계가 모두 통과한다.

```text
root: has_oos=0, oos_num_recs=0
p0:   has_oos=1, oos_num_recs=1
p1:   has_oos=0, oos_num_recs=0
```

## Verification

- Focused fixture: `oos_setup_db`, `test_oos_sql_show`, `oos_cleanup_db` 3/3 통과; 해당 GTest binary 5/5 통과.
- Configured OOS suite: 27/27 통과. owner descriptor, empty-page reclaim, growth-gate sweep, vacuum mock/real path, storage option, SQL UPDATE/DELETE 를 포함한다.
- Original 999-row hash-partition workload: SQL workload status 0, `COUNT(*)=999`, root `has_oos=0`, 네 child partition 모두 `has_oos=1`, workload 뒤 server 생존.
- 해당 local rerun 의 `backupdb` 단계는 기존 backup 과 이름이 충돌해 error -100 으로 끝났다. ownership 검증과 server 생존 결과에는 영향이 없지만, 이 실행을 backup/restart 성공 근거로 사용하지 않는다.
- `git diff --check` 및 pre-commit codestyle 통과.

## Review

### Standards

문서화된 coding-standard 위반은 없다. 비차단 설계 smell 로 nullable output pointer 와 여러 boolean 이 transform mode 를 암묵적으로 표현한다. 이번 최소 수정에서는 public surface 를 더 넓히지 않기 위해 유지했다.

### Specification

핵심 소유권 invariant 와 FORCE_OUTLINE blocker 는 해결됐다. `SHOW ALL HEAP OOS` test 가 root/selected/unselected heap 을 직접 구별한다.

남은 coverage opportunity 는 partitioned FORCE_OUTLINE DELETE 이후 vacuum reclaim 과 REPLACE/ODKU 전용 probe test 다. 현재 구현 검토와 전체 OOS suite 에서 결함은 발견되지 않았으며, 이 두 항목은 PR blocker 가 아니라 reviewer 요청 시 추가할 후속 검증이다.

## Publication Status

- Source commit pushed to PR #7600.
- Local and full OOS verification complete.
- CircleCI full-suite result: pending.
