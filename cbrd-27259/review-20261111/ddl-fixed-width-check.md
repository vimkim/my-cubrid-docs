# PR #8416 리뷰 코멘트 4536816663 분석: DDL 시점의 고정 길이 크기 검사

- 대상: https://github.com/CUBRID/cubrid/pull/8416#discussion_r4536816663 (hornetmj, `src/storage/heap_file.c:14867`)
- 기준 소스: PR head `89496263e` (`CBRD-27259-storage-force-inline`)
- 작성: 2026-11-11. 분석만 했으며 소스, TC, GitHub, JIRA는 바꾸지 않았다.

## 1. 목표와 결론 요약

이 문서는 작성자가 위 코멘트에 어떻게 답할지 정하도록 근거를 준다.

- **리뷰어 주장은 사실이다.** 두 예시 모두 PR head 빌드에서 그대로 재현했다 (2절).
- **원인은 이 PR이 만든 새 규칙이다.** 같은 스키마와 쓰기가 이전 OOS 브랜치 빌드에서는 성공했다. PR 이전에는 이 행들이 `REC_BIGONE` 으로 저장됐다.
- **DDL에는 행 크기 검사가 전혀 없다.** 다만 DDL은 고정 길이 부분의 크기를 이미 계산한다. 그래서 검사를 넣을 자리는 있다 (3절).
- **권고.** 이 PR에는 답글과 스펙/PR 본문 메모만 넣는다. DDL 검사는 별도 JIRA 후속으로 넘기되 `feature/oos-merge` 를 `develop` 에 병합하기 전에 끝낸다. 리뷰어가 병합 차단 조건으로 본다면 4절의 옵션 B를 이 PR에 넣는다. 이 경우 변경량은 중간 수준이다 (5절).

## 2. 리뷰어 주장과 검증

### 2.1 주장

이 PR부터 사용자 클래스 행이 한 페이지 (`heap_Maxslotted_reclength` = 16236바이트)를 넘으면 OOS 값이 없어도 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (-1396)로 거부된다. 그런데 CREATE TABLE과 ALTER ... ADD COLUMN은 고정 길이 컬럼만으로 이 한도를 넘는 스키마를 받는다. 그 결과 DDL은 성공하고 모든 쓰기가 실패한다.

- 예 1: `bit(136000)` 테이블에는 어떤 행도 넣을 수 없다.
- 예 2: `bit(120000)` 테이블에 `bit(16000)` 을 추가하면 기존 행의 모든 UPDATE와 새 INSERT가 실패한다. `unloaddb` 후 `loaddb` 도 0행이 된다.

### 2.2 코드 근거 (`89496263e`)

- `src/storage/heap_file.c:14866-14867` 에서 비시스템 클래스 행은 `has_oos` 와 무관하게 `heap_is_big_length` 이면 거부된다. PR 이전 조건은 `has_oos && heap_is_big_length` 였다 (코멘트의 diff hunk).
- `src/storage/heap_file.c:13663-13689` (`heap_attrinfo_get_record_payload_size`)는 고정 길이 컬럼을 값이 NULL이어도 `tp_domain_disk_size (domain)` 로 센다. 그래서 고정 길이 부분은 값과 무관한 하한이다.
- `src/storage/heap_file.c:13700-13724` (`heap_attrinfo_get_record_header_size`)의 헤더는 `OR_MVCC_INSERT_HEADER_SIZE` + 가변 오프셋 테이블 + NULL bitmap (`OR_BOUND_BIT_BYTES (고정 컬럼 수)`)이다. `heap_file.c:14859` 에서 MVCC 헤더 최대치와의 차이 (`OR_MVCC_MAX_HEADER_SIZE - OR_MVCC_INSERT_HEADER_SIZE` = 32 - 16)를 더한다.
- `heap_attrinfo_determine_disk_layout` (`heap_file.c:13743-13827`)의 OOS 후보는 가변 길이 컬럼뿐이다 (`!is_fixed`, `heap_file.c:13793-13795`). 고정 길이 컬럼은 OOS로 옮길 수 없다.
- DDL 쪽 행 크기 검사는 없다. `src/object/schema_manager.c`, `schema_template.c`, `class_object.c`, `src/query/execute_schema.c`, `src/parser/semantic_check.c` 에 `DB_PAGESIZE`, 최대 객체 크기, 행 크기 관련 오류가 없다. 옛 `ER_HEAP_OVERPASS_MAXOBJ_SIZE` (-54)는 `error_code.h` 정의 외에 사용처가 없다.

### 2.3 재현

PR head 설치본 `~/.cub/install/CBRD-27259-storage-force-inline/debug_gcc` (`cubrid_rel`: 11.5.0.2929-8949626)으로 SA 모드 (`csql -S`)에서 실행했다. DB는 `/home/vimkim/tk/rv-ddl-fixed-width-check/rvdb/rvfw` 이고, 스크립트는 같은 디렉터리의 `ex.sql`, `ex2.sql`, `ex3.sql` 이다. 서버는 띄우지 않았다.

| 문장 | PR head 결과 |
| --- | --- |
| `create table big_fixed (id int, image bit(136000))` | 성공 |
| `insert into big_fixed values (1, B'1')` | -1396, 17040 bytes |
| `insert into big_fixed (id) values (2)` (image NULL) | -1396, 17040 bytes |
| `create table photo (id int, view_count int, image bit(120000))` 후 15000바이트 값 INSERT | 성공 |
| `alter table photo add column thumbnail bit(16000)` | 성공 |
| `update photo set view_count = view_count + 1 where id = 1` | -1396, 17044 bytes |
| `update photo set thumbnail = NULL where id = 1` | -1396, 17044 bytes |
| `insert into photo (id) values (2)` | -1396, 17044 bytes |
| `select ... from photo` / `delete from photo where id = 1` | 읽기와 DELETE는 성공 |

리뷰어가 말하지 않은 경로도 확인했다.

| 문장 | PR head 결과 |
| --- | --- |
| 빈 테이블 `m2 (id int, b bit(8))` 에 `alter table m2 modify b bit(136000)` | 성공. 이후 쓰기는 모두 실패할 스키마다 |
| 행이 있는 `m1` 에 같은 MODIFY | -1396로 실패, 기존 행 유지 (`bit_length(b)` = 8) |
| `create table c1 under p1 (c bit(60000))`, `p1` 은 `bit(80000)` | 성공. `insert into c1` 은 -1396, 17540 bytes |
| `create table l1 like big_fixed` | 성공. INSERT는 -1396 |
| `bigint` 컬럼 2100개 테이블 | 성공. INSERT는 -1396, 17096 bytes |
| `bit(128000)` + `varchar(100)` | INSERT 성공. 하한 이하는 정상 |
| 경계 `id int, b bit(129600)` | INSERT는 -1396, 16240 bytes |

비교용으로 PR 이전 OOS 브랜치 설치본 `CBRD-26835-feat-oos-merge` (11.5.0.2687-17a58ab, 2026-09-21 빌드)에서 같은 `ex.sql` 을 돌렸다. 모든 INSERT, ALTER, UPDATE가 성공했다 (`big_fixed` 2행, `photo` 의 `view_count` = 1). 이 빌드는 PR의 정확한 base가 아니라 더 오래된 OOS 브랜치다. 그러나 해당 거부 조건이 `has_oos &&` 였다는 점은 diff hunk와 일치한다.

### 2.4 고정 부분 하한식

측정한 오류 크기는 모두 다음 식과 정확히 일치한다. 가변 컬럼이 없는 사용자 (MVCC) 클래스 기준이다.

`최소 행 크기 = OR_MVCC_MAX_HEADER_SIZE (32) + OR_BOUND_BIT_BYTES (고정 컬럼 수) + Σ tp_domain_disk_size (고정 컬럼)`

| 테이블 | 식 | 측정 |
| --- | --- | --- |
| `big_fixed` | 32 + 4 + (4 + 17000) | 17040 |
| `photo` (ALTER 후) | 32 + 4 + (4 + 4 + 15000 + 2000) | 17044 |
| `bit(129600)` | 32 + 4 + (4 + 16200) | 16240 |
| `bigint` × 2100 | 32 + 264 + 16800 | 17096 |

가변 컬럼이 있으면 가변 오프셋 테이블 `OR_VAR_TABLE_SIZE_INTERNAL (n_variable, offset_size)` 이 더해진다. 가변 값이 모두 NULL인 행이 하한이다. 이 경우 크기가 255바이트를 넘으므로 `offset_size` 는 2다 (`heap_file.c:13711-13716`).

**판정: 사실.** 두 예시와 설명 (NULL로 바꿔도 실패, DROP COLUMN 전까지 풀리지 않음)이 모두 맞다. MODIFY, UNDER, LIKE도 같은 틈이 있다.

## 3. DDL에서 검사할 수 있는 자리

- `src/object/class_object.c:7357-7396` (`classobj_install_template`)이 flatten된 템플릿의 instance attribute를 돌며 고정 길이 크기 합을 이미 계산한다. 결과는 `class_->fixed_size` 다 (`class_object.c:7485`). 이 함수에는 "class를 건드리기 전에 모든 실패를 처리한다"는 계약이 있다 (`class_object.c:7319-7321`).
- 이 함수는 `install_new_representation` (`src/object/schema_manager.c:12378`, 호출 `:12502`)에서만 불리고, 그 위는 `update_class` (`schema_manager.c:13166`)다. CREATE, ALTER ADD/MODIFY/CHANGE, UNDER, LIKE가 모두 이 경로를 지난다.
- 한도 `heap_Maxslotted_reclength` 는 서버 값이다. 클라이언트에서는 기존 API `heap_get_maxslotted_reclength` (`src/communication/network_interface_cl.h:139`)로 받는다. 지금은 `log_applier.c:9404` 만 쓴다.
- **주의.** `class_->fixed_size` 는 `DB_ATT_ALIGN` 으로 올림된 값이다 (`class_object.c:7396`). heap 검사는 올림 없는 합을 쓴다. 그대로 쓰면 경계에서 최대 3바이트의 false positive가 생긴다. 검사는 heap과 같은 식으로 다시 계산해야 한다.
- **주의.** `sm_add_constraint` 도 `sm_update_class_with_auth` 를 부른다 (`schema_manager.c:15000`, `:15038`). 이미 한도를 넘는 기존 테이블 (PR 이전에 만들어 `REC_BIGONE` 행을 가진 DB)에 단순 검사를 넣으면 ADD INDEX 같은 무관한 ALTER까지 막힌다. 따라서 "새 하한이 한도를 넘고, 이전 하한보다 커질 때만" 거부해야 한다. 그래야 DROP COLUMN으로 빠져나올 수 있다.

## 4. 범위 판단

**이 PR에 넣을 이유.**
- 이 틈은 이 PR이 만든 것이다. PR 이전에는 같은 스키마가 정상 동작했다 (2.3절). 고친 규칙이 DDL과 어긋나는 상태로 들어간다.
- 리뷰어는 규칙 자체에는 동의하고 일관성만 요청했다.

**후속으로 넘길 이유.**
- 새 오류 코드가 필요하다. -1396 메시지는 "레코드를 저장할 수 없다"는 쓰기 시점 문구라 DDL에 맞지 않는다. `error_code.h`, 각 locale 메시지, 호환 헤더를 고쳐야 한다.
- 정할 스펙이 남아 있다. 기존 초과 테이블의 ALTER를 허용할지, 시스템 클래스와 VCLASS를 어떻게 뺄지, 상속 전파 중 실패를 어떻게 되돌릴지다.
- 대상이 좁다. 사용자 타입 중 큰 고정 길이 타입은 사실상 `BIT(n)` 뿐이다 (`CHAR` 는 CBRD-26663 이후 가변 길이, OOS-CONTEXT.md "bigone Rejection"). 나머지는 수천 개의 고정 컬럼이다.
- 병합 대상이 `feature/oos-merge` 라서 `develop` 병합 전에 후속을 끝낼 시간이 있다.
- 스펙 근거. OOS-CONTEXT.md "bigone Rejection (CBRD-26937, CBRD-27259)"은 2026-11-09에 쓰기 시점 거부만 정했고 DDL 검사는 정하지 않았다. 새 요구다.

**판단.** 후속 이슈가 맞다. 단, 이 PR에서 그 사실을 스펙과 PR 본문에 적어야 한다.

## 5. 선택지

| 옵션 | 내용 | 장점 | 단점 |
| --- | --- | --- | --- |
| A. 답글만 | 의도된 스펙이라고 답한다 | 변경 없음 | 알려진 함정이 문서 없이 남는다. 리뷰어가 받아들이기 어렵다 |
| **B. 이 PR에 DDL 검사** | `update_class` 의 flatten 뒤에 하한을 계산하고, 새 오류 코드로 거부한다. 3절의 두 주의를 지킨다. SQL TC로 CREATE, ADD, MODIFY, UNDER, LIKE, 경계, 기존 초과 테이블의 ADD INDEX를 확인한다 | 함정이 사라진다. 리뷰 한 번에 끝난다 | 소스 약 50~80줄과 오류 코드, 메시지, TC가 필요하다 (추정). 스펙 결정이 리뷰 중에 늘어난다. CI를 다시 돌려야 한다 |
| **C. 메모 + 후속 JIRA (권고)** | PR 본문 Remarks와 OOS-CONTEXT.md에 "DDL은 고정 길이 하한을 검사하지 않는다"를 적는다. CBRD-27259 아래 후속 Sub-task로 옵션 B를 등록하고 `develop` 병합 전 완료로 둔다 | 이 PR 범위가 유지된다. 스펙 결정을 따로 리뷰한다 | `feature/oos-merge` 에 함정이 잠시 남는다 |
| D. 규칙 되돌리기 | non-OOS `REC_BIGONE` 을 다시 허용한다 | DDL 문제가 없어진다 | 2026-11-09에 확정한 스펙을 뒤집는다. 리뷰어도 원하지 않는다 |

**권고는 C.** 리뷰어가 병합 전에 필요하다고 하면 B로 바꾼다. B를 택해도 3절의 "이전 하한보다 커질 때만" 조건은 꼭 지켜야 한다.

### false positive 위험 (옵션 B 설계 시)

- **NULL bitmap.** 고정 컬럼 수로만 계산한다 (`n_attributes - n_variable`). 가변 컬럼을 넣으면 과대 계산이 된다.
- **가변 오프셋.** 가변 값이 모두 NULL인 행이 하한이다. `(n_variable + 1)` 개 항목에 `offset_size` = 2를 쓴다. 가변 컬럼의 선언 크기를 더하면 안 된다. `VARCHAR(20000) STORAGE FORCE_INLINE` 처럼 값에 따라 들어갈 수도 있는 스키마를 막게 된다.
- **MVCC 헤더.** 사용자 클래스는 MVCC 클래스다. heap 검사처럼 `OR_MVCC_MAX_HEADER_SIZE` (32)를 쓰면 쓰기 시점 판정과 정확히 같다. 더 작게 잡으면 놓치는 경우가 생길 뿐 잘못 막지는 않는다.
- **정렬.** 올림된 `fixed_size` 를 쓰면 최대 3바이트 오차가 생긴다 (3절).
- **한도 값.** 페이지 크기에 따라 달라지므로 상수를 쓰지 말고 서버 값을 받는다.
- **기존 DB.** 이미 초과한 테이블의 무관한 ALTER를 막지 않아야 한다 (3절). `unloaddb` 한 스키마를 `loaddb` 할 때는 CREATE가 실패한다. 행 단위 -1396 대신 클래스가 없다는 오류로 바뀐다. 어느 쪽이든 데이터는 들어가지 않는다.
- **HA.** DDL은 SQL 문장으로 복제된다. 업그레이드 중 버전이 다른 slave가 DDL을 거부하면 복제가 멈출 수 있다 (추정, 확인 안 함).

## 6. 다른 코멘트와의 관계

- 4536816653 (ALTER FORCE_INLINE 후 unload/load 실패)도 "DDL은 받고 이후 쓰기에서 거부"라는 같은 모양이다. 그러나 가변 컬럼의 FORCE_INLINE은 값에 따라 들어갈 수도 있어서 DDL 하한 검사로는 막을 수 없다. 이 문서의 옵션 B는 그 코멘트를 해결하지 않는다.
- 4536816674 (heap 계층 `REC_BIGONE` debug assert)는 같은 hunk에 달렸지만 주제가 다르다.
- 참고. JIRA CBRD-27259 본문의 수락 기준 5 ("non-OOS `REC_BIGONE` 은 계속 허용")는 2026-11-09에 확정한 OOS-CONTEXT.md의 거부 규칙과 어긋난다. 본문을 갱신하지 않은 상태다. 리뷰어가 근거를 찾다가 이 차이를 볼 수 있으니 함께 고치는 것이 좋다.

## 7. 답글 초안

> 확인 감사합니다. 말씀하신 두 예시를 PR head(`89496263e`)에서 그대로 재현했습니다. `bit(136000)` 테이블은 NULL만 넣어도 17040바이트로 거부되고, `photo` 는 ALTER 후 UPDATE와 INSERT가 17044바이트로 거부됩니다. 빈 테이블의 `ALTER ... MODIFY`, `CREATE TABLE ... UNDER`, `CREATE TABLE ... LIKE` 도 같은 스키마를 만들 수 있습니다. 이 PR 이전에는 이 행들이 `REC_BIGONE` 으로 저장됐으므로, 이 PR이 만든 틈이 맞습니다.
>
> 고정 길이 컬럼은 값이 NULL이어도 자리를 차지하므로 최소 행 크기는 스키마만으로 정해집니다 (MVCC 헤더 최대 32바이트 + NULL bitmap + 고정 길이 크기 합). DDL에서 이를 검사하는 것이 맞다고 봅니다.
>
> 다만 이 검사에는 새 오류 코드가 필요하고, 정할 것이 몇 가지 있습니다. 이미 한도를 넘는 기존 테이블에 ADD INDEX 같은 무관한 ALTER를 허용하는 조건, 상속과 파티션 전파, 시스템 클래스 제외입니다. 그래서 이 PR에서는 PR 설명과 OOS 명세에 현재 제약을 적고, DDL 검사는 CBRD-27259 아래 후속 이슈로 등록해 `feature/oos-merge` 를 develop에 병합하기 전에 처리하려 합니다. 이 PR 병합 전에 필요하다고 보시면 말씀해 주세요. 이 PR에 넣겠습니다.

## 8. 확인하지 않은 것

- 정확한 PR base (`feature/oos-merge` 현재 tip) 빌드에서의 비교. 대신 더 오래된 OOS 브랜치 빌드 (`17a58ab`)를 썼다.
- CS 모드 실행. SA 모드만 돌렸다. 거부는 서버 쪽 함수라 결과가 같다고 추정한다.
- 리뷰어 예 2의 `unloaddb` → `loaddb` 0행. PR 본문 rev4가 이미 인정한 동작이며 직접 돌리지 않았다.
- 파티션 테이블, `CREATE TABLE ... AS SELECT`, `ALTER ... CHANGE`, 상속 전파 중 ALTER 실패의 원자성.
- 최대 컬럼 수 제한. 2100개 `bigint` 는 허용됐다.
- `NCHAR` 등 다른 고정 길이 문자 타입의 현재 분류. OOS-CONTEXT.md는 `CHAR` 만 가변 길이로 명시한다.
- 옵션 B의 실제 구현과 변경량. 50~80줄은 추정이다.
