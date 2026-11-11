# PR #8416 리뷰 코멘트 4536816674 분석: heap 계층 REC_BIGONE debug assert

- PR: https://github.com/CUBRID/cubrid/pull/8416 (head `89496263e`, base `feature/oos-merge`)
- 코멘트: https://github.com/CUBRID/cubrid/pull/8416#discussion_r4536816674 (`src/storage/heap_file.c:14865`)
- 작성일: 2026-11-11. 분석만 했다. 엔진·TC·GitHub·JIRA는 바꾸지 않았다.

## 목표

리뷰어의 별도 이슈 요청에 어떻게 답할지 정할 근거를 만든다. 리뷰어 주장이 맞는지, 이 PR 범위인지 후속인지, 가장 작은 올바른 대응이 무엇인지 확인한다.

## 리뷰어 주장 요약

1. 이 PR은 "사용자 클래스 행은 REC_BIGONE이 되지 않는다"는 원칙을 행 배치 함수(`heap_attrinfo_transform_to_disk_internal`) 한 곳에서만 지킨다.
2. heap 계층은 길이만 보고 REC_BIGONE을 고른다. 그래서 행 배치 함수를 거치지 않는 writer가 생기면 원칙이 조용히 깨진다.
3. 경로별 상태는 다음과 같다. SQL·서버 loaddb·workspace·파티션 재분배는 거부한다. HA 반영(`xlocator_repl_force`)은 마스터 레코드를 그대로 옮긴다. SA compactdb(`disk_update_instance`)는 `desc_obj_to_disk`가 OOS를 몰라 REC_BIGONE을 만든다.
4. CBRD-27924 처리 뒤 `heap_insert_logical`의 여러 페이지 분기, `heap_update_bigone`, `heap_update_relocation`의 큰 레코드 분기에 "대상 클래스가 시스템 클래스"라는 debug assert를 넣자고 요청한다.
5. release 동작은 바뀌지 않으므로 HA 반영을 멈출 위험이 없다고 본다.
6. 이 PR의 승인 여부와는 별개라고 명시했다.

## 판정: 대체로 사실이다. 단, assert 위치 목록에 알려진 우회 경로가 빠져 있다

주장 1~3, 5는 코드와 재현으로 확인했다. 주장 4의 위치 목록은 불완전하다. 알려진 유일한 우회인 SA compactdb는 REC_HOME 행을 `heap_update_home`으로 갱신한다. 리뷰어가 제안한 세 지점에는 이 함수가 없다. 그대로 넣으면 바로 그 경로를 잡지 못한다.

### 근거 1. heap 계층은 길이만 본다

- `heap_is_big_length`는 `length > heap_Maxslotted_reclength`만 비교한다(`src/storage/heap_file.c:1124`).
- 거부 검사는 행 배치 함수 한 곳에만 있다(`src/storage/heap_file.c:14862-14872`). 주석도 "the heap layer does not check"라고 적는다. `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`를 설정하는 곳은 소스 전체에서 이 한 곳뿐이다(grep).
- OOS 명세의 bigone 절도 같은 사실을 적는다. heap 계층은 검사하지 않고, SA compactdb(CBRD-27924), HA replica apply, 시스템·루트 클래스 레코드는 REC_BIGONE을 저장할 수 있다(`cubrid-oos-context` `f7796c1`, `OOS-CONTEXT.md:113`).

### 근거 2. heap에서 multipage(REC_BIGONE) 데이터를 쓰는 지점은 여섯 곳이다

heap 파일의 overflow 쓰기는 `heap_ovf_insert`(`heap_file.c:6289`)와 `heap_ovf_update`(`heap_file.c:6318`)를 거친다. `overflow_insert`/`overflow_update`를 heap_file.c에서 직접 부르는 곳은 이 두 함수뿐이다. 호출자는 다음과 같다.

| # | 함수 (호출 줄) | 상황 | 리뷰어 목록 | `context->class_oid` |
|---|---|---|---|---|
| 1 | `heap_insert_handle_multipage_record` (23237) | INSERT. `heap_insert_logical`(26186)이 부름 | 있음 ("heap_insert_logical 여러 페이지 분기") | 있음 |
| 2 | `heap_update_home` (25707) | REC_HOME → REC_BIGONE 갱신 | **없음** | 있음 |
| 3 | `heap_update_relocation` (25377) | REC_RELOCATION → REC_BIGONE 갱신 | 있음 | 있음 |
| 4 | `heap_update_bigone` (25152, `heap_ovf_update`) | REC_BIGONE → REC_BIGONE 갱신 | 있음 | 있음 |
| 5 | `heap_delete_home` (24816) | MVCC delete가 DELID를 붙여 커진 행 | 없음 | 있음 |
| 6 | `heap_delete_relocation` (24323) | 같은 상황, relocation 행 | 없음 | 있음 |

`heap_update_logical`은 원래 레코드 유형으로 분기한다. REC_HOME과 REC_ASSIGN_ADDRESS는 `heap_update_home`으로 간다(`heap_file.c:26740-26753`).

### 근거 3. SA compactdb 우회를 head `8949626`에서 재현했다

설치본 `~/.cub/install/CBRD-27259-storage-force-inline/debug_gcc`(11.5.0.2929 debug)를 SA 모드로만 썼다. 서버는 띄우지 않았다. DB는 `/home/vimkim/tk/rv-heap-bigone-assert/bigdb`에 있다. 픽스처는 CBRD-27924의 재현과 같다.

```sql
CREATE TABLE t (id INT, a BIT VARYING) DONT_REUSE_OID;
INSERT INTO t VALUES (1, X'abab…');                          -- 3000B
ALTER TABLE t ADD COLUMN b BIT VARYING DEFAULT X'cdcd…';     -- 21000B, lazy default
```

`SHOW SLOTTED PAGE SLOTS WHERE VOLUME=1 AND PAGE=641` 관측 결과는 다음과 같다.

| 시점 | slot 1 Type | Length | `SHOW HEAP OOS OF t` |
|---|---|---|---|
| ALTER 뒤 | `HOME` | 3028 | Has_oos_file 0 |
| `cubrid compactdb -S -v bigdb dba.t` 뒤 | `BIGONE` | 8 | Has_oos_file 0 |

compactdb 뒤에도 값 길이는 3000·21000B로 보존됐다. REC_HOME 행이 REC_BIGONE이 됐다. 근거 2의 분기에 따라 이 쓰기는 `heap_update_home`을 지난다(코드로 추론). CBRD-27924의 2026-11-04 debugger 관측(Engine `e3589ae`)도 `heap_update_home` → `heap_ovf_insert` → `overflow_insert` stack을 기록했다. 이 PR은 `compactdb.c`를 바꾸지 않았다(`git diff origin/feature/oos-merge...HEAD --stat`).

같은 행을 SQL UPDATE로 다시 쓰면 OOS로 분리된다. 이번 세션에서는 재현하지 않았고, CBRD-27924 표(일반 UPDATE 2576B, HAS_OOS)를 근거로 든다.

### 근거 4. 리뷰어 경로 표의 나머지 행

- SA compactdb. `disk_update_instance`는 `desc_obj_to_disk` 결과를 `heap_update_logical`에 바로 넘긴다(`src/executables/compactdb.c:666, 704-705`). 행 배치 함수를 거치지 않는다. 주장과 같다.
- HA 반영. `xlocator_repl_force`는 받은 recdes로 `locator_insert_force`/`locator_update_force`를 부른다(`src/transaction/locator_sr.c:7868, 7889`). 재배치는 OOS OID fixup뿐이다(7851). 마스터 이미지를 그대로 쓴다. 주장과 같다.
- workspace·loaddb 수신. 사용자 클래스면 `locator_finalize_oos_record`가 준비 여부를 판단한다(`locator_sr.c:5408-5409`). `DB_PAGESIZE / 4 - OR_MVCC_MAX_HEADER_SIZE`를 넘는 레코드는 항상 재배치 대상이다(`src/storage/heap_oos.cpp:129`). 그래서 REC_BIGONE 크기의 레코드는 행 배치 함수의 검사를 받는다. 이 PR의 `LoaderRejectsEveryBigoneUserRecord` 단위 테스트가 이 경로를 확인한다. 주장과 같다.
- SQL과 파티션 재분배. 이번에는 코드를 따로 추적하지 않았다. 리뷰어 표와 PR 테스트를 그대로 받아들였다.

### 근거 5. assert에 필요한 값은 싸게 얻는다

- 여섯 지점 모두 `HEAP_OPERATION_CONTEXT *context`를 받고, `context->class_oid`가 있다(`src/storage/heap_file.h:289`).
- `oid_is_system_class`는 29개 항목의 정적 배열을 선형 비교한다(`src/storage/oid.c:386-391`, `oid_is_cached_class_oid` 350-363). 큰 레코드 분기 안에서만 부르면 비용은 무시할 수준이다. debug 빌드 전용이다.
- 행 배치 함수의 거부 조건도 같은 술어(`oid_is_system_class`)를 쓴다. assert와 거부 기준이 어긋나지 않는다.

### assert 설계 시 주의점

1. **NULL class_oid.** `oid_is_system_class`는 `!OID_ISNULL`을 assert한다(`oid.c:388`). `tde.c:213`은 class_oid NULL로 insert context를 만든다(TDE keyinfo heap). assert는 `OID_ISNULL (&context->class_oid) || oid_is_system_class (&context->class_oid)` 형태여야 한다.
2. **cache 초기화 시점.** 카탈로그 클래스 OID는 restart 때 `catcls_find_and_set_cached_class_oid`가 채운다(`src/transaction/boot_sr.c:2476`). 루트 클래스는 `boot_get_db_parm`이 먼저 채운다. createdb 도중 cache가 비어 있을 때 큰 카탈로그 행이 쓰이면 오탐이 날 수 있다. 추론이며 확인하지 않았다. 클래스 객체(루트 클래스 heap)는 cache 0번이라 안전하다.
3. **cache에 없는 시스템 클래스.** `dual`, `_db_global_tran`은 `oid_Cache`(`oid.c:87-117`)에 없다. 행 배치 함수도 이들을 사용자 클래스로 다루므로 기준은 일관된다. 실제로 큰 행이 생기지도 않는다.
4. **delete 두 지점.** 이 PR은 MVCC 헤더 최대치를 크기에 넣는다. 따라서 새 규칙으로 받아들인 행은 delete로 REC_BIGONE이 되지 않는다. 그러나 규칙 이전에 만들어진 행은 다르다. 예를 들어 OOS 이전 데이터가 있는 DB에서 최대 길이에 가까운 REC_HOME 행을 지우면 5·6번 지점에 도달할 수 있다. 그런 DB를 debug 빌드로 다루면 assert가 정상 데이터에서 터진다. 추론이며 재현하지 않았다.
5. **순서.** CBRD-27924 수정 전에 2번 지점에 assert를 넣으면 debug 빌드의 SA compact TC(`gap_compact_sa_cs` 등)가 assert로 죽는다. 리뷰어가 제안한 순서(27924 뒤)가 맞다.

## 범위: 이 PR이 아니라 후속이다

- 리뷰어 스스로 승인과 별개라고 했다.
- assert를 지금 넣으면 2번 지점에서 SA compactdb가 debug 빌드로 실패한다. 이를 피하려면 27924 수정을 이 PR에 끌어와야 한다. 27924는 OOS 배치 적용, 거부한 행의 처리 방식 결정, TC 기대값 검증을 포함하는 별도 작업이다.
- CBRD-27924(상태 Confirmed, 담당 Daehyun Kim, Target guava)는 이미 "OOS 대상 값이 없는 큰 행도 SA compact가 REC_BIGONE으로 쓰지 않는다"를 Acceptance Criteria로 갖는다. 2026-11-09 범위 추가에서 이 PR의 명세 변경과 heap 계층 무검사도 기록했다. assert는 이 이슈를 닫는 검증 장치로 자연스럽게 들어간다.

## 선택지

| 선택지 | 장점 | 단점 |
|---|---|---|
| A. 답글만 | 비용 없음 | 리뷰어 요청이 추적되지 않는다. 위치 목록의 누락도 남는다 |
| **B. 답글 + CBRD-27924 AC 추가 (권장)** | 우회 제거와 그 회귀 방지를 한 이슈에서 끝낸다. 2번 지점 누락을 바로잡아 기록한다. 새 티켓이 없다 | 27924 범위가 조금 커진다 |
| C. 답글 + 새 JIRA 하위 이슈 | assert 작업이 독립적으로 보인다 | 27924에 의존하는 작은 작업이 하나 더 생긴다. 순서 관리가 늘어난다 |
| D. 이 PR에 assert 추가 | 원칙을 곧바로 구조로 고정한다 | SA compact debug TC가 실패한다. 27924를 끌어와야 해서 PR 범위가 커진다 |

### 권장: B

CBRD-27924에 다음 AC를 더한다.

> heap 계층에서 multipage(REC_BIGONE) 데이터를 쓰는 insert·update 지점에 debug assert를 둔다. 대상은 `heap_insert_handle_multipage_record`, `heap_update_home`, `heap_update_relocation`, `heap_update_bigone`의 큰 레코드 분기다. 조건은 `OID_ISNULL (&context->class_oid) || oid_is_system_class (&context->class_oid)`이다. delete 두 지점(`heap_delete_home`, `heap_delete_relocation`)은 규칙 이전 데이터 때문에 제외하거나, 제외하지 않으면 그 이유를 기록한다. debug 빌드에서 unit·SQL·shell 회귀와 `gap_compact_sa_cs`가 assert 없이 통과함을 확인한다.

구현 형태는 둘 중 하나다. 첫째는 static helper 하나를 네 분기에서 부르는 방식이다. 둘째는 `heap_ovf_insert`/`heap_ovf_update`에 class OID 인자를 더해 함수 안에서 한 번만 검사하는 방식이다. 둘째는 앞으로 생길 호출자도 자동으로 잡는다. 대신 delete 지점까지 포함되므로 주의점 4의 결정이 먼저 필요하다.

## 리뷰어 답글 초안

> 좋은 제안 감사합니다. 확인해 보니 말씀하신 대로 거부 검사는 행 배치 함수에만 있고, heap 계층은 길이만 보고 REC_BIGONE을 고릅니다. 현재 head(8949626)에서 SA compactdb를 실행하면 3028B REC_HOME 행이 REC_BIGONE으로 바뀌는 것도 재현했습니다.
>
> 한 가지 보탤 점이 있습니다. SA compactdb가 갱신하는 행은 대개 REC_HOME이라서 `heap_update_home`의 큰 레코드 분기(`heap_ovf_insert` 호출)를 지납니다. 그래서 assert 위치에 `heap_insert_logical`(실제로는 `heap_insert_handle_multipage_record`), `heap_update_bigone`, `heap_update_relocation` 외에 `heap_update_home`도 넣어야 알려진 우회를 잡을 수 있습니다. 조건은 tde keyinfo처럼 class OID가 없는 heap을 고려해 `OID_ISNULL (class_oid) || oid_is_system_class (class_oid)`로 두려고 합니다. MVCC delete로 커지는 `heap_delete_home`/`heap_delete_relocation`은 규칙 이전에 저장된 행에서 정상적으로 도달할 수 있어 따로 판단하겠습니다.
>
> 이 PR에 지금 넣으면 debug 빌드의 SA compact 테스트가 assert에 걸리므로, CBRD-27924의 Acceptance Criteria에 추가해 SA compactdb 수정과 함께 처리하겠습니다.

## 다른 두 코멘트와의 관계

- 4536816663(DDL 고정 길이 검사)과 4536816653(ALTER FORCE_INLINE 뒤 unload/load)은 "정상 경로가 거부되는 사용성 문제"를 다룬다. 이 코멘트는 "거부를 우회하는 경로를 debug에서 잡자"는 반대 방향의 요청이다.
- DDL 검사를 추가해도 assert 위치나 조건은 바뀌지 않는다. 겹치는 작업은 없다.
- 세 코멘트 모두 같은 거부 규칙(`heap_file.c:14862-14872`)을 기준으로 삼는다. 답글에서 그 규칙의 범위("행 배치 함수를 거치는 비시스템 클래스 행")를 같은 말로 설명하면 일관된다.

## 확인하지 않은 것

- assert를 실제로 넣은 빌드와 회귀. 공유 worktree라 빌드하지 않았다.
- createdb 중 oid cache가 비어 있을 때 큰 카탈로그 행이 쓰이는지(주의점 2).
- 규칙 이전 데이터에서 delete 지점에 실제로 도달하는지(주의점 4).
- SQL UPDATE와 파티션 재분배 경로의 코드 추적. 리뷰어 표와 PR 테스트를 받아들였다.
- 같은 픽스처의 SQL UPDATE 비교. CBRD-27924 표를 인용했다.
- 재현은 16KB page, debug 빌드 한 번이다. 재현 DB는 `/home/vimkim/tk/rv-heap-bigone-assert/bigdb`에 남겨 두었다.
