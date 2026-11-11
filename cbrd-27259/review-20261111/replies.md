# PR #8416 리뷰 5857391949 답글과 후속 작업 초안

- 리뷰: hornetmj, 2026-11-11, 코멘트 3개.
- 결정 (작성자, 2026-11-11): 1번은 이 PR에서 고친다. 2번은 후속 JIRA로 넘기고 명세와 PR 본문에 제약을 적는다. 3번은 CBRD-27924 완료 조건에 넣는다.
- 분석 근거: 같은 디렉터리의 `alter-force-inline-unload.md`, `ddl-fixed-width-check.md`, `heap-bigone-assert.md`.

## 답글 1. discussion_r4536816653 (ALTER FORCE_INLINE 뒤 unloaddb → loaddb)

> 확인 감사합니다. 말씀하신 두 증상 모두 재현했습니다. ALTER로 `FORCE_INLINE` 을 건 뒤 `view_count` 만 바꾸는 UPDATE가 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 실패했고, unloaddb 결과를 새 DB에 loaddb하면 그 행이 거부되어 0행이 됐습니다.
>
> `87f6f85` 에서 고쳤습니다. `FORCE_INLINE` 을 새로 얻는 ALTER는 이제 그 ALTER에 보이는 기존 행을 모두 새 정책으로 배치해 보고, 한 행이라도 한 페이지를 넘으면 같은 오류로 ALTER를 실패시킵니다. 값은 여전히 옮기지 않습니다. 그래서 ALTER가 성공한 테이블은 이 이유로 UPDATE나 loaddb가 실패하지 않습니다.
>
> - 서버의 기존 ALTER 행 재작성 경로(`xlocator_upgrade_instances_domain`)에 검사 전용 모드를 더했습니다. 파티션 테이블은 모든 파티션을 검사합니다.
> - 예시의 `article` 은 ALTER가 거부되고 정책이 그대로 남습니다. 큰 행을 지운 뒤에는 ALTER가 성공하고, unloaddb → loaddb도 모든 행이 적재됩니다.
> - 단위 테스트 `AlterForceInlineRejectsRowThatNoLongerFits` 와 SQL TC `cbrd_27259_alter_force_inline_existing_rows` 를 추가했습니다.
> - OOS 명세의 정책 변경 절에도 이 규칙을 적었습니다.
>
> 비용은 ALTER가 테이블 전체를 한 번 읽는 것입니다. `FORCE_INLINE` 을 새로 얻는 경우에만 읽습니다.

## 답글 2. discussion_r4536816663 (DDL 시점의 고정 길이 크기 검사)

> 확인 감사합니다. 두 예시를 PR head에서 그대로 재현했습니다. `bit(136000)` 테이블은 NULL만 넣어도 17040바이트로 거부되고, `photo` 는 ALTER 뒤 UPDATE와 INSERT가 17044바이트로 거부됩니다. 빈 테이블의 `ALTER ... MODIFY`, `CREATE TABLE ... UNDER`, `CREATE TABLE ... LIKE` 도 같은 스키마를 만들 수 있습니다. 이 PR 전에는 이런 행이 `REC_BIGONE` 으로 저장됐으므로, 이 PR이 만든 틈이 맞습니다.
>
> 고정 길이 컬럼은 값이 NULL이어도 자리를 차지하므로, 최소 행 크기는 스키마만으로 정해집니다(MVCC 헤더 최대 32바이트 + NULL bitmap + 고정 길이 크기 합). DDL에서 검사하는 것이 맞다고 봅니다.
>
> 다만 이 검사에는 새 오류 코드가 필요하고, 정할 것이 몇 가지 있습니다.
> - 이미 한도를 넘는 기존 테이블에서 ADD INDEX 같은 무관한 ALTER를 허용하는 조건
> - 상속과 파티션 전파
> - 시스템 클래스 제외
>
> 그래서 이 PR에서는 OOS 명세와 PR 설명에 현재 제약을 적고, DDL 검사는 CBRD-28051(https://jira.cubrid.org/browse/CBRD-28051)로 등록했고, `feature/oos-merge` 를 develop에 병합하기 전에 처리하겠습니다. 이 PR 병합 전에 필요하다고 보시면 말씀해 주세요.

## 답글 3. discussion_r4536816674 (heap 계층 REC_BIGONE debug assert)

> 좋은 제안 감사합니다. 확인해 보니 말씀하신 대로 거부 검사는 행 배치 함수에만 있고, heap 계층은 길이만 보고 REC_BIGONE을 고릅니다. PR head에서 SA compactdb를 실행하면 3028바이트 REC_HOME 행이 REC_BIGONE으로 바뀌는 것도 재현했습니다.
>
> 한 가지 보탭니다. SA compactdb가 갱신하는 행은 대개 REC_HOME이라 `heap_update_home` 의 큰 레코드 분기(`heap_ovf_insert` 호출)를 지납니다. 그래서 assert는 `heap_insert_handle_multipage_record`, `heap_update_bigone`, `heap_update_relocation` 외에 `heap_update_home` 에도 있어야 알려진 우회를 잡습니다.
>
> 조건은 tde keyinfo처럼 class OID가 없는 heap을 고려해 `OID_ISNULL (class_oid) || oid_is_system_class (class_oid)` 로 두려고 합니다. MVCC delete로 커지는 `heap_delete_home` 과 `heap_delete_relocation` 은 규칙 이전에 저장된 행에서 정상적으로 도달할 수 있어 따로 판단하겠습니다.
>
> 이 PR에 지금 넣으면 debug 빌드의 SA compact 테스트가 assert에 걸리므로, CBRD-27924의 완료 조건에 넣어 SA compactdb 수정과 함께 처리하겠습니다.

## JIRA 초안 A. 새 후속 이슈 (DDL 고정 길이 크기 검사)

- 유형: Improvement (CBRD-27259 관련)
- 제목: CREATE·ALTER가 고정 길이 부분만으로 한 페이지를 넘는 테이블을 거부한다

설명:

- **배경.** CBRD-27259(PR #8416)부터 사용자 테이블 행은 `REC_BIGONE` 이 필요하면 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 거부된다. 고정 길이 컬럼은 OOS로 옮길 수 없고 NULL이어도 자리를 차지한다. 그래서 고정 길이 부분이 한도를 넘는 테이블에는 어떤 행도 쓸 수 없다.
- **문제.** DDL은 이 조건을 검사하지 않는다. 다음 DDL이 모두 성공한 뒤 모든 쓰기가 실패한다.
  - `CREATE TABLE`
  - `ALTER ... ADD`, `MODIFY`, `CHANGE`
  - `UNDER`
  - `LIKE`
- **예.** `create table big_fixed (id int, image bit(136000))` 는 성공한다. 그 뒤 모든 INSERT가 17040바이트로 거부된다.
- **원하는 결과.** 고정 길이 하한이 한도(`heap_Maxslotted_reclength`)를 넘는 스키마를 DDL 시점에 거부한다.
  - 하한식: `OR_MVCC_MAX_HEADER_SIZE + OR_BOUND_BIT_BYTES (고정 컬럼 수) + Σ tp_domain_disk_size (고정 컬럼)`. 가변 컬럼이 있으면 가변 오프셋 테이블을 더한다.
  - 이미 한도를 넘는 기존 테이블의 무관한 ALTER(ADD INDEX 등)는 막지 않는다. 하한이 이전보다 커질 때만 거부한다.
  - 시스템 클래스와 VCLASS는 제외한다.
  - 새 오류 코드와 메시지를 쓴다.
- **완료 조건.** `feature/oos-merge` 를 develop에 병합하기 전에 끝낸다. CREATE, ADD, MODIFY, UNDER, LIKE, 경계, 기존 초과 테이블의 ADD INDEX를 SQL TC로 확인한다.
- **근거.** PR #8416 리뷰 discussion_r4536816663. 분석은 `my-cubrid-docs/cbrd-27259/review-20261111/ddl-fixed-width-check.md`.

## JIRA 초안 B. CBRD-27924 완료 조건 추가

> heap 계층에서 multipage(REC_BIGONE) 데이터를 쓰는 insert·update 지점에 debug assert를 둔다. 대상은 `heap_insert_handle_multipage_record`, `heap_update_home`, `heap_update_relocation`, `heap_update_bigone` 의 큰 레코드 분기다. 조건은 `OID_ISNULL (&context->class_oid) || oid_is_system_class (&context->class_oid)` 이다. delete 두 지점(`heap_delete_home`, `heap_delete_relocation`)은 규칙 이전 데이터 때문에 제외하거나, 포함하면 그 이유를 기록한다. debug 빌드에서 unit·SQL·shell 회귀와 `gap_compact_sa_cs` 가 assert 없이 통과함을 확인한다. (PR #8416 리뷰 discussion_r4536816674)
