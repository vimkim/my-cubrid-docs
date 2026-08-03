# [CBRD-27089] Write OOS value chains to the pruned partition's heap

- JIRA: https://jira.cubrid.org/browse/CBRD-27089
- Base branch: `feat/oos`
- Source commit: `2ed0e60511c9c865aefa013589b007e431840cbe`
- Author host: Claude Code (claude)

## Purpose

파티션 테이블에 OOS (큰 컬럼 값을 heap 레코드 밖 별도 파일에 저장하는 방식) 대상 레코드를 쓸 때, OOS 값 체인 (값을 담는 실제 저장 단위의 연결) 이 잘못된 heap 의 OOS 파일에 기록되는 문제를 고친다.

- **AS-IS (1)**: 파티션 테이블에 OOS 대상 레코드를 쓰면, OOS 값 체인은 **루트 클래스의 heap** 에 딸린 OOS 파일에 기록되고 레코드 자체는 **파티션의 heap** 에 저장된다. 파티션 heap 헤더에 OOS VFID (OOS 파일 식별자) 가 없으므로 vacuum 이 불변식 위반을 감지한다. 현재 `feat/oos` 에 심어 둔 병합 전 계측 (`vacuum_oos.cpp` 의 `abort()`) 때문에 cub_server 크래시로 나타나지만, 계측을 걷어낸 뒤의 지속 동작은 "해당 레코드의 OOS 정리 건너뛰기" — 즉 **파티션 테이블의 모든 OOS 행이 영구 저장 공간 누수**가 된다. 더 나아가 파티션 heap 에 이미 자기 OOS 파일이 있는 경우 (예: 파티션 지정 INSERT 가 먼저 그 파일을 만든 경우) vacuum 은 유효한 VFID 를 찾았다고 판단하고 **엉뚱한 파일의 VFID 로 `oos_delete` 를 호출**할 수 있다 — abort 보다 위험한 무증상 오삭제 경로다.
- **TO-BE (1)**: OOS 값 체인은 항상 **레코드가 실제로 저장되는 heap** 의 OOS 파일에 기록된다. OOS 행이 실제로 들어간 파티션에만 OOS 파일이 (지연) 생성되며, 파티션 테이블의 루트 클래스 heap 에는 OOS 파일이 더 이상 생기지 않는다 — QA 가 확인할 수 있는 관찰 가능한 불변식이다.
- **AS-IS (2)**: `REPLACE` / `INSERT ... ON DUPLICATE KEY UPDATE` 가 중복 키 탐색용으로만 만들고 버리는 임시 레코드 이미지도 진짜 OOS 값 체인을 기록해서, 삽입되지 않는 이미지의 체인이 고아로 남았다 (파티션 여부와 무관한 잠재 누수).
- **TO-BE (2)**: 탐색용 이미지는 OOS 억제 모드로 만들어 체인을 아예 기록하지 않는다.

이 수정이 QA 시나리오 `_02_show_archive_log_header` (해시 파티션 4개 + 1MB VARCHAR 999건, 매뉴얼 빌드 `11.5.0.2437-11aa26f` 2개 호스트 재현 크래시, develop 병합 게이트 P0 — JIRA 기준) 를 해소한다.

### 근본 원인

서버측 INSERT/UPDATE 는 `locator_attribute_info_force` (`src/transaction/locator_sr.c`) 에서 다음 순서로 진행된다.

```text
locator_attribute_info_force
 ├ 1. locator_allocate_copy_area_by_attr_info
 │     └ heap_attrinfo_transform_to_disk
 │        └ heap_attrinfo_transform_to_disk_internal      ← 레코드 직렬화
 │           └ heap_attrinfo_insert_to_oos                ← ★ OOS 값 체인 기록
 │              └ heap_oos_insert_serialized_values (attr_info->class_oid)   ← 루트 클래스!
 └ 2. locator_insert_force
       └ partition_prune_insert                           ← ★ 이제서야 파티션 결정
          └ or_set_rep_id (rep_id 비트만 교체)            ← 레코드 바이트는 그대로
```

즉 **OOS 기록(1)이 파티션 결정(2)보다 먼저** 일어난다. 1단계의 OOS 기록은 `attr_info->class_oid` (INSERT 대상으로 지정된 루트 클래스) 기준으로 heap 을 찾으므로 체인이 루트 클래스 heap 의 OOS 파일에 들어가고, 2단계 프루닝은 recdes (레코드의 직렬화된 디스크 이미지) 의 representation id 비트만 파티션 것으로 바꾼 채 (`src/query/partition.c` 의 shortcut) OOS inline stub (외부화된 값을 가리키는 16바이트 참조) 를 그대로 든 레코드를 파티션 heap 에 넣는다.

SELECT 는 stub 안의 head OOS OID (절대 물리 주소) 로 값을 직접 읽기 때문에 정상 동작했고, heap 헤더의 VFID 를 필요로 하는 vacuum 만 이 어긋남을 감지했다.

**영향 범위**: OOS demotion (큰 컬럼을 OOS 로 내리는 결정) 은 레코드 전체 크기가 `DB_PAGESIZE / 4` (기본 16KB 페이지에서 약 4KB) 를 넘고 16바이트보다 큰 가변 컬럼이 있으면 발동한다 (`heap_attrinfo_determine_disk_layout`). 따라서 이 버그와 이번 수정 경로는 1MB 급 값에 한정되지 않고, **약 4KB 를 넘는 모든 파티션 테이블 행**에 해당한다.

### 증거 (일회성 진단 계측)

원인 확정을 위해 쓰기 시점 tripwire (불변식 위반 지점에서 즉시 중단시키는 일회성 진단 코드) 를 심고 재현 시나리오를 돌렸다. 이 계측은 커밋에 포함되지 않았으므로 아래 로그는 재현 절차가 아니라 분석 기록이다. 첫 행 INSERT 에서 바로 잡혔다.

```text
stage=OOS_MAPPING_CREATE class_oid=0|195|3 hfid=1|576|577 oos_vfid=1|896   ← 루트 클래스에 OOS 파일 생성
stage=WRITE_GUARD INSERT  class_oid=0|195|6 target_hfid=1|704|705          ← 레코드는 파티션 heap 으로
```

수정 후 같은 시나리오에서는 파티션 클래스 4개 (`0|209|3`~`0|209|5`, `0|196|8`) 의 heap 에 각각 OOS 파일이 생성되고 루트 클래스에는 생성되지 않았으며, guard 는 한 번도 발화하지 않았다.

## Implementation

### 설계 결정: 왜 "2-pass 변환"인가

검토한 대안과 배제 이유:

| 대안 | 내용 | 배제 이유 |
|---|---|---|
| vacuum 측 fallback | 파티션 heap 에서 VFID 를 못 찾으면 루트 클래스 heap 을 다시 조회 | "heap 파일 : OOS 파일 = 1 : 1" 불변식이 깨진다. `ALTER TABLE ... DROP PARTITION` 시 파티션 레코드의 체인이 루트 OOS 파일에 영구 누수된다 |
| 파티션 헤더에 루트 OOS VFID 공유 기록 | 모든 파티션 heap 헤더가 루트의 OOS 파일을 가리키게 함 | OOS 파일이 여러 heap 에 공유되어 drop/truncate 경로가 전부 위험해진다 (파티션 drop 이 공유 파일을 파괴) |
| 프루닝 후 체인 이주 | 일단 루트에 쓰고, 프루닝 후 읽어서 파티션 파일로 옮김 | 행마다 값 전체를 다시 읽고 다시 쓰는 이중 I/O (1MB 행 999건이면 약 2GB 추가 I/O) |
| 값 기반 프루닝 신설 | recdes 없이 attr_info 의 DB_VALUE 로 파티션을 결정하는 새 API | 올바른 방향이지만 `partition.c` 프루닝 기계 전반을 건드리는 큰 리팩터링. P0 수정 범위를 넘는다 |
| **2-pass 변환 (채택)** | 1차 변환은 OOS 억제 (전량 inline), 그 이미지로 기존 recdes 기반 프루닝을 먼저 수행, OOS 가 필요할 때만 파티션을 목적지로 2차 변환 | 기존 프루닝 API 를 그대로 재사용. OOS 미대상 행은 기존과 동일한 단일 패스. 불변식 유지 |

참고로 heap 계층은 이미 같은 문제를 같은 방식으로 푼 선례가 있다: REC_BIGONE (한 페이지를 넘는 레코드의 overflow 저장) 변환은 프루닝이 끝난 뒤 `heap_insert_logical` 안에서 일어나므로 overflow 파일은 항상 올바른 heap 에 만들어진다. OOS 기록도 장기적으로는 heap 계층으로 내리는 것 (프루닝 이후 시점) 이 이상적이며, 이번 2-pass 는 그 방향과 충돌하지 않는 최소 수정이다.

### 변경 내용

**`src/storage/heap_file.c` / `heap_file.h`**

- `heap_attrinfo_determine_disk_layout`: `suppress_oos`, `would_demote_oos` 파라미터 추가. 억제 모드에서는 demotion 을 실제로 수행하지 않고 "수행했을 것인가"만 보고한다.
- `heap_attrinfo_transform_to_disk_internal`: `oos_class_oid` (OOS 체인을 받을 클래스 지정), `would_demote_oos`, `increments_already_applied` 파라미터 추가.
- 신규 공개 래퍼 2개:
  - `heap_attrinfo_transform_to_disk_probe_oos` — 1차 패스. OOS 억제 + demotion 필요 여부 보고. LOB 복사와 `INCR()` / `DECR()` 반영 같은 attr_info 부수효과는 **locator 의 2-pass 안에서** 정확히 한 번 일어난다 (아래 참고).
  - `heap_attrinfo_transform_to_disk_oos_class` — 2차 패스. 체인을 지정 클래스 (프루닝된 파티션) 의 heap 에 기록. 1차 패스가 이미 `INCR()` / `DECR()` 를 반영했다고 가정하고 다시 적용하지 않는다 (`incremented_attrids` 를 미리 채워서 이중 적용 차단). LOB 는 기존 `HEAP_WRITTEN_LOB_ATTRVALUE` 상태 전이가 이중 복사를 막는다.
- `heap_attrinfo_insert_to_oos`: `oos_class_oid` 파라미터 추가. NULL 이면 기존대로 `attr_info->class_oid`.

**`src/transaction/locator_sr.c` / `locator_sr.h`**

- `locator_allocate_copy_area_by_attr_info`: `oos_class_oid`, `probe_would_demote_oos` 파라미터 추가, 위 래퍼로 분기.
- `locator_attribute_info_force` (INSERT / UPDATE 공통 copyarea (레코드 이미지를 담는 임시 버퍼) 빌드 지점):
  - `pruning_type != DB_NOT_PARTITIONED_CLASS` 이면 1차 패스 (OOS 억제) 로 레코드를 만든다.
  - demotion 이 필요할 때만: 그 inline 이미지로 `partition_prune_insert` / `partition_prune_update` 를 미리 호출해 파티션을 알아낸 뒤, 2차 패스로 체인을 파티션 heap 에 기록한 최종 레코드를 다시 만든다.
  - 이후 흐름 (`locator_insert_force` / `locator_update_force` 의 자체 프루닝, 잠금, scancache (heap 접근 캐시) 교체) 은 그대로 재사용한다. 프루닝은 결정적 (같은 값 → 같은 파티션) 이므로 사전 프루닝과 본 프루닝의 결과가 항상 일치한다. 단, 본 프루닝은 생략되는 것이 아니라 실제로 다시 수행된다 — 비용은 아래 "파급 효과 정리" 참고.
- 비파티션 경로와 MVCC 재평가 경로 (`locator_mvcc_reev_cond_assigns`) 는 기존 단일 패스 그대로다.

**`src/query/query_executor.c`**

- `qexec_remove_duplicates_for_replace` (REPLACE), `qexec_oid_of_duplicate_key_update` (ON DUPLICATE KEY UPDATE): 중복 키 탐색용으로만 쓰고 버리는 레코드 이미지를 억제 모드로 생성하게 변경. 기존에는 이 probe 변환도 진짜 OOS 값 체인을 기록해서, 삽입되지 않는 이미지의 체인이 그대로 고아로 남는 잠재 누수가 있었다. 이 변경은 **파티션 여부와 무관하게** 적용된다.

### 파급 효과 정리

- 비파티션 테이블: INSERT/UPDATE 경로는 기존과 동일 (probe/2-pass 미사용). 단 REPLACE / ON DUPLICATE KEY UPDATE 의 probe 변환은 파티션 여부와 무관하게 억제 모드로 바뀌어, 고아 OOS 체인이 더 이상 생기지 않는다 (유익한 동작 변화).
- 파티션 테이블 + OOS 미대상 행 (약 4KB 이하): 1차 패스 결과가 기존 단일 패스와 동일하므로 그대로 사용한다. 추가 비용 없음.
- 파티션 테이블 + OOS 대상 행 (약 4KB 초과): **직렬화 1회 + 프루닝 1회가 추가**된다. 프루닝 중 stub 해소를 위한 `oos_read` (파티션 키 컬럼 자체가 OOS 로 내려간 경우에만 발생) 는 1차 프루닝에서는 없지만 `locator_insert_force` 의 본 프루닝에서 그대로 발생하므로 상쇄 효과는 없다. 정직한 비용 프로파일은 "행당 직렬화 2회 + 프루닝 2회"다.
- probe 이미지는 전량 inline 이므로 행 크기만큼의 임시 copyarea 를 잡는다 (`VARCHAR(1000000)` 행이면 약 1MB). OOS+bigone 거부 게이트가 probe 모드에서는 적용되지 않으므로 slotted record 상한과 무관하게 커질 수 있고, 동시 writer 수 × 행 크기만큼 서버 메모리 피크가 늘어난다. 삽입에 직접 쓰이지 않는 임시 이미지라는 전제가 각 호출부에서 지켜져야 한다.
- 파티션 간 이동 UPDATE (파티션 키 변경): 기존 코드에서는 새 체인이 이전 파티션의 OOS 파일에 남아 위 AS-IS (1) 의 오삭제 경로에 노출되는 더 위험한 케이스였다. 이번 수정으로 새 체인이 목적지 파티션 파일에 기록된다. 1MB OOS 행의 실제 파티션 간 이동 (`t2__p__p0` → `t2__p__p2`) 을 standalone 모드에서 수행해 쓰기 경로 라우팅과 데이터 정합성 (총 행수, 값 동등성, `DISK_SIZE`) 을 확인했고, 이때 standalone 의 즉시 정리 경로 (`heap_oos_delete_unreferenced`) 가 두 파티션의 OOS 파일에 걸쳐 오류 없이 수행됨도 함께 확인했다. 다만 **client-server 모드에서 이동된 행의 이전 버전을 vacuum 이 회수하는 경로는 별도 검증이 필요하다** (아래 한계 / 후속 작업 참고).

## Remarks

### 검증

디버그 빌드에서 수행했다. `enable_string_compression` 은 기본값이 `yes` 인데, QA 페이로드 (`RPAD (ROWNUM, 1000000, ' ')`) 는 거의 전부 공백이라 압축되면 demotion 임계값 (약 4KB) 아래로 내려가 OOS 경로 자체를 타지 않는다. 그래서 QA 시나리오와 동일하게 `enable_string_compression=no` 로 검증했다 (기본 설정에서는 이 시나리오가 OOS 를 건드리지 않고 정상 완료함도 별도 확인).

- QA 재현 시나리오 (해시 파티션 4개, 1MB VARCHAR 999건 INSERT): abort 없음, `COUNT(*)=999`, `DISK_SIZE(col1)=1000012` (압축이 꺼져 값이 원본 크기 그대로 저장되었음을 확인하는 조회), 파티션 heap 4개에 OOS 파일 각각 생성 + 루트 클래스에는 미생성 (일회성 진단 계측으로 확인 후 계측 제거).
- `backupdb -l 0`, UPDATE 200건 + DELETE 100건, vacuum 처리 대기 (60초 이상), 서버 재시작 (recovery + heap 헤더 VFID 지속성) 후 1MB 값 동등성 조회까지 정상.
- 파티션 간 이동 UPDATE: 1MB OOS 행을 파티션 키 변경으로 `t2__p__p0` 에서 `t2__p__p2` 로 이동 (standalone 모드). 총 행수 999 유지, 이동된 값 동등성 조회 1건, `DISK_SIZE=1000012` 정상.
- 비파티션 OOS CRUD (INSERT/UPDATE/DELETE/SELECT, 500KB~600KB 값), 파티션 테이블 REPLACE / ON DUPLICATE KEY UPDATE 정상.
- 단위 테스트: `-DUNIT_TESTS=ON` 빌드에서 ctest 테스트 24개 전부 통과 (OOS 스위트 포함).

### 리뷰 포인트

1. `locator_attribute_info_force` 의 2-pass 분기 — INSERT 와 UPDATE fallthrough 가 같은 블록을 지나므로 `LC_IS_FLUSH_INSERT` 분기와 에러 시 copyarea 해제 경로를 봐 달라.
2. `increments_already_applied` — `INCR()` / `DECR()` 이 locator 2-pass 에 걸쳐 정확히 한 번만 반영되는지. 주의: REPLACE / ODKU 의 probe 는 이 플래그 없이 이후 본 변환과 이어지는 별개 시퀀스다 (probe 가 increment 를 반영하고 본 변환은 `increments_already_applied=false` 로 돈다). `INCR()` 이 REPLACE/ODKU 경로에서 실제로 도달 가능한지는 확인하지 못했다 — 도달 가능하다면 수정 전부터 있던 이중 적용 이슈로, 이번 변경으로 새로 생기지는 않는다.
3. **잠금 순서 변화** — 기존에는 OOS 파일 생성이 항상 루트 heap (DML 이 이미 잠근 대상) 에서 일어났지만, 이제 2차 패스가 파티션 heap 헤더에 파일을 만들 수 있는 시점이 `locator_insert_force` 의 `lock_subclass (IX_LOCK)` **이전**이다. DML 의 루트 클래스 잠금이 `ALTER TABLE ... DROP / REORGANIZE PARTITION` (루트 X 잠금) 과 직렬화되므로 안전하다고 판단했지만, 이 판단을 리뷰에서 검증해 달라.
4. probe 모드 recdes 는 heap 최대 레코드 길이 (`heap_Maxslotted_reclength`) 를 넘을 수 있는 임시 이미지다. 삽입에 직접 쓰이지 않는다는 전제가 각 호출부에서 지켜지는지.
5. 1차 패스의 `would_demote_oos` 와 2차 패스의 실제 demotion 판단이 이론상 어긋날 수 있다 (1차 패스가 LOB ELO locator 문자열을 재작성해 컬럼 크기가 바뀌는 경우). 어긋나도 결과는 "전량 inline 레코드 (필요시 REC_BIGONE)" 로 안전하지만, 이 비대칭을 인지하고 봐 달라.

### 한계 / 후속 작업

- HA 복제 적용 경로 (`locator_oos_insert_force`) 는 마스터가 로그에 남긴 class_oid 기준으로 동작하며 이번 수정 범위 밖이다. 마스터가 파티션 클래스를 기록하므로 수정 후 동작과 일관된다.
- loaddb 서버 로더는 `pruning_type = DB_NOT_PARTITIONED_CLASS` 고정이므로 이번 변경의 영향을 받지 않는다.
- `redistribute_partition_data` (ALTER ... REORGANIZE) 는 레코드를 전량 inline 으로 펼쳐 재삽입하므로 OOS 행이 REC_BIGONE 으로 바뀌는 기존 동작이 남아 있다 (별도 이슈 후보).
- 장기적으로 OOS 기록을 heap 계층 (`heap_insert_logical`, 프루닝 이후) 으로 내리면 2-pass 없이 단일 패스로 돌아갈 수 있다. REC_BIGONE 변환과 같은 위치다.
- 이번 수정 전 만들어진 데이터 (루트 OOS 파일에 체인이 있는 DB) 는 마이그레이션하지 않는다. `feat/oos` 는 미출시 브랜치이므로 QA 는 DB 재생성으로 충분하다.
- **후속 검증 항목**: client-server 모드에서 파티션 간 이동 UPDATE 후, 이동된 행의 이전 버전을 vacuum 이 회수하는 경로 (이전 파티션 OOS 파일의 옛 체인 `oos_delete`). standalone 모드의 쓰기 경로/즉시 정리 검증은 완료했으나 이 vacuum 경로는 이번 검증 세션에서 수행하지 못했다.

### Test Plan

```bash
# 재현 (수정 전: vacuum worker abort / 수정 후: 정상 완료)
cubrid createdb --db-volume-size=20M --log-volume-size=20M tmpdb en_US.utf8
# cubrid.conf: enable_string_compression=no  (기본값 yes; 공백 페이로드가 압축되면 OOS 를 타지 않으므로 필요)
cubrid server start tmpdb
csql -u dba tmpdb <<'SQL'
CREATE TABLE t2 (col1 VARCHAR (1000000), col2 VARCHAR (50))
PARTITION BY HASH (col1) PARTITIONS 4;
INSERT INTO t2 (col1, col2)
SELECT RPAD (ROWNUM, 1000000, ' '), ROWNUM FROM db_root CONNECT BY LEVEL < 1000;
SELECT COUNT (*) FROM t2;                          -- 999
SELECT DISK_SIZE (col1) FROM t2 LIMIT 1;           -- 1000012 (비압축 확인)
UPDATE t2 SET col2 = col2 || 'u' WHERE ROWNUM <= 200;
DELETE FROM t2 WHERE ROWNUM <= 100;
SELECT COUNT (*) FROM t2;                          -- 899
-- 파티션 간 이동 UPDATE (해시가 우연히 같은 파티션이면 접미사를 바꿔 재시도)
UPDATE t2 SET col1 = RPAD ('moved1', 1000000, ' ')
 WHERE col1 = (SELECT MAX (col1) FROM t2);
SELECT COUNT (*) FROM t2;                          -- 899 (행 수 불변)
SQL
cubrid backupdb -l 0 tmpdb
sleep 60                                           # vacuum 이 INSERT/UPDATE/DELETE 로그 블록을 처리할 시간
cubrid server status                               # 서버 생존 = 불변식 위반 없음
cubrid server stop tmpdb && cubrid server start tmpdb   # recovery + heap 헤더 VFID 지속성
csql -u dba tmpdb -c "SELECT COUNT(*) FROM t2;"    # 899 (ROWNUM 기반 DELETE 라 특정 값 생존은 비결정적이므로 행 수로 확인)
```

파티션별 행 위치는 파티션 클래스 직접 조회 (`SELECT COUNT(*) FROM t2__p__p0 WHERE col1 = ...` 등) 로 확인할 수 있다.

단위 테스트: `./build.sh -m debug -c "-DUNIT_TESTS=ON"` 후 ctest (OOS 스위트 포함 24개 테스트 전부 통과).
