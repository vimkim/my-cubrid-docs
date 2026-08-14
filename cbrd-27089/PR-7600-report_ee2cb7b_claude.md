# PR #7600 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7600](https://github.com/CUBRID/cubrid/pull/7600)
**제목:** [CBRD-27089] Write OOS value chains to the pruned partition's heap
**작성자:** vimkim
**HEAD SHA:** `ee2cb7be534853b4052cf6c42b007d74e0bf809f`
**리뷰 일시:** 2026-08-14

> **TL;DR** (Blocking): OOS (큰 컬럼 값을 heap 레코드 밖 별도 파일에 저장하는 기능) 억제 모드를 `STORAGE FORCE_OUTLINE` (레코드 크기와 무관하게 컬럼 값을 항상 OOS 로 내리는 컬럼 옵션) 컬럼이 우회한다. `FORCE_OUTLINE` demote (컬럼 값을 OOS 파일로 내보내는 동작) 만으로 레코드가 게이트 (demote 를 시작하는 레코드 크기 임계; 현재 코드 기준 `DB_PAGESIZE / 4`) 아래로 내려가면 2차 패스가 생략되어 CBRD-27089 버그가 그대로 재현되고, 다른 케이스에서도 루트 OOS 파일 생성, 고아 체인, 불필요한 INSERT 실패가 생긴다. 원인은 `heap_attrinfo_determine_disk_layout` 한 함수 -- 여기만 고치면 머지 가능. 작성자가 요청한 리뷰 포인트 5개는 모두 검증 통과했다.

## Summary

- **변경 요약**: 파티션 쓰기를 2-pass 로 바꿔 OOS 값 체인이 레코드가 실제 저장되는 파티션 heap 의 OOS 파일에 기록되게 하고, REPLACE / ON DUPLICATE KEY UPDATE 의 중복 키 탐색용 이미지가 체인을 만들지 않게 한다
- **주요 이슈**: `FORCE_OUTLINE` 컬럼이 억제 모드를 우회 (Blocking 1건)
- **확인 필요 사항**: MVCC 재평가 경로에서 파티션 키를 바꾸는 assignment 가 도달 가능한지 (Question 1건)

---

## Findings

### Blocking (must fix)

- `src/storage/heap_file.c:12338-12351` -- `FORCE_OUTLINE` demote 루프가 억제 여부와 무관하게 `selected` 와 `*has_oos` 를 설정하므로, 억제 모드 (probe: OOS 값 체인을 쓰지 않아야 하는 1차 변환) 의 모든 케이스에서 `heap_attrinfo_insert_to_oos` 가 실제 체인을 기록한다. 이때 `oos_class_oid == NULL` 이면 `attr_info->class_oid` (파티션 쓰기에서는 루트 클래스) 로 기록한다 (`heap_file.c:12753`; probe 래퍼 `heap_attrinfo_transform_to_disk_probe_oos` 는 항상 `NULL` 을 넘긴다). 게이트 미달 레코드에서는 여기에 더해 `suppress_oos` 검사 (`heap_file.c:12381`) 가 크기 게이트 if 블록 (`heap_file.c:12359`) 안에 중첩되어 있어 아예 실행되지 않는다. 또한 `*would_demote_oos` 는 `oos_candidates` 로만 설정되는데 (`heap_file.c:12385`) 후보 수집이 이미 선택된 컬럼을 제외하므로 (`heap_file.c:12369`) `FORCE_OUTLINE` demote 는 2차 패스 트리거에 잡히지 않는다.

  ```c
  /* heap_file.c:12346-12349 -- 크기 게이트(12359) 바깥에서 무조건 실행.
   * suppress_oos 검사(12381)는 게이트 안쪽에 있어 게이트 미달 시 실행되지 않는다 */
  (*oos_plan)[i].selected = true;
  ...
  *has_oos = true;
  ```

  파티션 테이블 + `FORCE_OUTLINE` 컬럼 조합에서 케이스별 결과:

  | Case | Consequence |
  |---|---|
  | `FORCE_OUTLINE` demote 후 레코드가 게이트 이하이거나 다른 demote 후보가 없음 | `would_demote_oos == false` -> 2차 패스 생략 -> probe 가 루트 클래스 OOS 파일에 쓴 체인을 가리키는 stub (외부화된 값을 가리키는 16바이트 참조) 을 든 레코드가 파티션 heap 에 삽입 -> **CBRD-27089 재현** (vacuum abort / 영구 누수) |
  | 게이트 초과 + 다른 후보 존재, inline 이미지가 `heap_Maxslotted_reclength` (한 페이지에 담을 수 있는 레코드 상한; `DB_PAGESIZE` 에서 페이지/슬롯 오버헤드를 뺀 값이라 page 크기에 따라 약 4KB~16KB; `heap_file.c:3716`) 이하 | probe 이미지는 폐기되지만 체인은 이미 루트에 기록됨 -> 고아 체인 (아무 레코드도 참조하지 않아 vacuum 도 회수 불가) + 루트 클래스에 OOS 파일 생성 (PR 의 TO-BE 불변식 위반) |
  | inline 이미지가 `heap_Maxslotted_reclength` 초과 | `has_oos == true` 라서 OOS+`REC_BIGONE` (여러 페이지에 걸치는 오버플로 레코드 저장 형태) 거부 (`heap_file.c:13385`) 가 probe 에서 발화 -> 정상 처리 가능해야 할 행이 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 INSERT 실패 |
  | REPLACE / ON DUPLICATE KEY UPDATE probe (`query_executor.c:11863`, `:12106`) | 파티션 여부와 무관하게 `FORCE_OUTLINE` 체인이 여전히 기록되어 고아로 남음 -- 새 주석이 약속하는 "no OOS value chain is written" 미달성 |

  `FORCE_OUTLINE` 은 사용자 도달 가능한 SQL 문법이다 (`src/parser/csql_grammar.y:10539`). 수정 방향: (a) 억제 모드에서는 `FORCE_OUTLINE` 루프를 보고 전용으로 바꿔 `selected` 와 `*has_oos` 는 건드리지 않고 `*would_demote_oos = true` 만 설정하고, (b) 게이트 안의 기존 조기 반환은 유지하되 `*would_demote_oos` 를 덮어쓰지 않고 누적한다.

### Non-blocking (should consider)

- `src/transaction/locator_sr.c:7736,7743` -- `pcontext` (파티션 프루닝에 필요한 파티션 목록/표현식 캐시) 가 `NULL` 인 호출자 (예: `qexec_execute_increment`, `src/query/query_executor.c:14250`) 는 사전 프루닝과 본 프루닝이 컨텍스트를 각각 load (`src/query/partition.c:3627-3651`) 하고 clear (`partition.c:3686`) 하므로 OOS 대상 행마다 컨텍스트가 2회 구축된다. 성능만의 문제이며 정확성 영향 없음.

### Questions for the author

- `src/transaction/locator_sr.c:13853` -- 이 PR 이 바꾼 동작은 아니고 (인자 `NULL, NULL` 추가만) 기존부터 단일 패스인 경로다: MVCC 재평가 (`locator_mvcc_reev_cond_assigns`) 는 체인을 `curr_attrinfo->class_oid` (원본 파티션) 에 기록한다. 재평가 assignment 가 파티션 키를 바꿔 행이 다른 파티션으로 가는 케이스가 이 경로에서 도달 가능한가? 가능하다면 "체인은 레코드가 저장되는 heap 의 OOS 파일에" 불변식이 여기서도 깨진다.

## Verified Review Points

PR 본문이 요청한 리뷰 포인트 5개 전부 확인했고 문제 없음:

1. **2-pass 에러 경로**: probe 실패와 재변환 실패는 `if (copyarea == NULL)` (`locator_sr.c:7768`) 로 수렴하고, 프루닝 실패는 `copyarea` (레코드 이미지를 담아 전달하는 임시 버퍼) 해제 + `NULL` 후 `locator_sr.c:7754` 의 `break` 로 빠진다 -- 세 경로 모두 누수, 이중 해제 없음. `assert (LC_IS_FLUSH_UPDATE)` 도 안전: 이 블록에 도달하는 case 라벨은 INSERT 3개 + UPDATE 3개뿐이고 `LC_FLUSH_INSERT_OOS` 는 `default:` 로 빠진다.
2. **INCR/DECR 이중 적용 차단**: pre-mark (`heap_file.c:13337`) 는 `qdata_increment_dbval` 재적용만 차단하고 (소비 지점 `heap_file.c:12980`) 1차 패스에서 증가된 값은 그대로 기록된다 -- 정확히 1회 반영.
3. **잠금 순서**: DML 이 루트 클래스 `IX_LOCK` (의도 배타 잠금) 을 선보유하고 (`query_executor.c:12861`) `ALTER ... DROP / REORGANIZE PARTITION` 은 루트 `SCH_M` (스키마 변경 잠금) 이 필요해 직렬화된다. 2차 패스가 `lock_subclass` (`locator_sr.c:4997`) 이전에 파티션 heap 헤더에 OOS 파일을 만들어도 안전 -- 작성자 판단 유효.
4. **probe 이미지 미삽입**: 두 `query_executor.c` call site 모두 키 추출 (`heap_attrvalue_get_key`, `heap_attrinfo_read_dbvalues`; `:11873`, `:11905`, `:12116`, `:12141`) 에만 사용하고 삽입하지 않는다.
5. **사전/본 프루닝 일치**: 본 프루닝은 OOS inline stub 을 attribute 계층에서 head OOS OID (체인 첫 레코드의 절대 물리 주소) 로 해소하므로 (`src/query/partition.c:3500` -> `heap_file.c:10979` -> `:10757` -> `:10452` -> `oos_read`) 체인이 어느 파일에 있든 같은 값 -> 같은 파티션. 파티션 키 컬럼 자체가 demote 된 QA 시나리오도 이 경로로 동작한다.

## JIRA Context

CBRD-27089 (P0, vacuum abort) 의 근본 원인 -- OOS 기록이 파티션 결정보다 먼저 일어나 루트 클래스 파일에 체인이 들어가는 것 -- 을 제거하는 PR 로, 티켓 의도와 일치한다. 단 위 Blocking 건 때문에 `FORCE_OUTLINE` 컬럼에서는 같은 원인이 그대로 남는다.
