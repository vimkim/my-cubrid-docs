# PR #8416 리뷰 코멘트 4536816653 분석: ALTER ... STORAGE FORCE_INLINE 후 unloaddb/loaddb

- 대상: https://github.com/CUBRID/cubrid/pull/8416#discussion_r4536816653 (리뷰어 hornetmj)
- 기준 커밋: PR head `89496263e` (`CBRD-27259-storage-force-inline`, base `feature/oos-merge`)
- 명세: `OOS-CONTEXT.md` (sha256 `426f2944…`, Last updated 2026-11-09)
- 작성일: 2026-11-11. 분석만 했고 엔진, TC, GitHub, JIRA에는 아무것도 쓰지 않았습니다.

## 1. 리뷰어 주장

큰 값이 이미 OOS에 있는 컬럼에 `ALTER ... STORAGE FORCE_INLINE` 을 걸면 스키마만 바뀌고 값은 OOS에 남습니다.
`unloaddb` 는 스키마에 `STORAGE FORCE_INLINE` 을 실어 내립니다.
`loaddb` 는 스키마를 먼저 만들고 데이터를 넣으므로, 그 값을 행 안에 둬야 하고 한 페이지를 넘어 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` 로 거부됩니다.
같은 이유로 원본 DB에서도 그 행의 무관한 컬럼 UPDATE가 실패합니다.
리뷰어는 ALTER가 값을 옮기지 않는 것이 의도라면 그 상태의 DB도 unloaddb/loaddb로 옮길 수 있어야 한다고 요청합니다.

## 2. 판정: 사실 (두 주장 모두 재현)

### 2.1 코드 근거 (`89496263e`)

- `src/query/execute_schema.c:12025-12037` 는 `do_change_att_schema_only` 안에서 정책 flag만 바꿉니다. 정책만 바뀌는 MODIFY는 row update 경로(`is_srv_update_needed`, `execute_schema.c:11032-11034`)를 타지 않으므로 저장된 값은 그대로입니다.
- `src/storage/heap_file.c:13792-13795` 는 `FORCE_INLINE` 컬럼을 demotion 후보에서 뺍니다. UPDATE는 행 전체를 현재 정책으로 다시 배치하므로, OOS에 있던 20000B 값이 행 안으로 돌아오고 bigone guard에 걸립니다.
- `src/executables/unload_schema.c:3095-3097` 는 스키마 flag를 보고 `STORAGE FORCE_INLINE` 을 출력합니다. 출력 위치는 `ALTER CLASS ... ADD ATTRIBUTE` 이고, schema 파일은 데이터보다 먼저 적재됩니다.

### 2.2 명세 근거

- `OOS-CONTEXT.md:109` (2026-11-05 수용): "ALTER does not relocate stored values; a policy applies when a write lays out the record."
- `OOS-CONTEXT.md:104`: `FORCE_INLINE` 값은 후보가 아니며, 행이 맞지 않으면 쓰기를 거부합니다. "Never ignore `FORCE_INLINE` to avoid that rejection."
- 따라서 UPDATE 실패와 loaddb 거부는 둘 다 현재 명세를 따른 결과입니다. 명세는 이 상태의 unloaddb/loaddb 왕복 여부를 다루지 않습니다.
- 이전 리뷰(`review-20261106/report.md:59`, D1)는 UPDATE 실패를 "spec-conformant, product decision"으로 기록했습니다. 그 사례는 작은 값이 demotion돼도 큰 inline 값을 구하지 못하는 경우입니다. 이번 코멘트는 큰 값 자체가 ALTER 전에 OOS에 있던 경우이고, unloaddb/loaddb 실패는 새 지적입니다.
- PR 본문 rev4 23행은 "ALTER는 이미 OOS에 있는 값을 옮기지 않습니다"라고 적었습니다. 29행의 "unloaddb와 loaddb 후 정책과 값의 저장 위치가 그대로 유지"는 8000B 값(`implementation-observations.md:70`) 기준이고, 이 사례에는 맞지 않습니다.

### 2.3 재현 (측정, SA 모드, install `debug_gcc` 11.5.0.2929, 디렉터리 `/home/vimkim/tk/rv-alter-force-inline-unload`)

```sql
create table article (id int, view_count int, content bit varying);
insert into article values (1, 0, CAST(REPEAT('AA', 20000) AS BIT VARYING));
alter table article modify content bit varying storage force_inline;   -- Execute OK
select id, view_count, bit_length(content)/8 from article;              -- 1, 0, 20000
update article set view_count = view_count + 1 where id = 1;
```

```
ERROR: The record cannot be stored because its size (20056 bytes) exceeds the maximum record size
(16236 bytes) after moving eligible variable-length columns to out-of-row storage (OOS). ...
```

unloaddb 결과 schema 파일:

```
ALTER CLASS [dba].[article] ADD ATTRIBUTE
       ...
       [content] bit varying(1073741823) STORAGE FORCE_INLINE;
```

새 DB에 `loaddb -S --schema-file --data-file`:

```
Start object loading.
Line 3:The record cannot be stored because its size (20056 bytes) exceeds the maximum record size (16236 bytes) ...
```

대상 DB의 `select count(*) from article` 는 0이고, 스키마는 `FORCE_INLINE` 으로 만들어졌습니다.

추가로 확인한 것(측정):

- `create table article2 like article; insert into article2 select * from article;` 도 같은 오류로 실패합니다. 같은 DB 안의 복사도 막힙니다.
- `alter table article modify content bit varying storage default;` 후에는 같은 UPDATE가 성공합니다(`view_count` 1). 사용자가 복구할 수 있는 길은 있습니다.

## 3. 범위: 이 PR

- `FORCE_INLINE` 은 이 PR이 처음 넣는 정책입니다. base `feature/oos-merge` 에는 이 상태를 만들 방법이 없습니다.
- 다른 정책 변경(`DEFAULT`, `PREFER_INLINE`, `FORCE_OUTLINE`)은 배치 힌트일 뿐이라 옮기지 않아도 다음 쓰기가 실패하지 않습니다. 옮기지 않는 ALTER가 쓸 수 없는 상태를 만드는 경우는 `FORCE_INLINE` 획득 하나입니다.
- unloaddb/loaddb는 버전 이전과 DB 재구성에 쓰는 기본 경로입니다. 이 PR의 JIRA 초안(`my-cubrid-jira/issues/CBRD-27259-storage-force-inline_bc8a895_codex.md:128,146`)도 unload/load 전달 경로 검증을 완료 조건으로 둡니다.
- 그래서 결함은 이 PR이 만든 것이고, 고치든 문서로 남기든 결정은 이 PR에서 해야 한다고 판단합니다. 후속 이슈로 넘기려면 리뷰어의 동의가 필요합니다.

## 4. 선택지

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| A1 검증만 | `FORCE_INLINE` 을 새로 얻는 ALTER가 기존 행을 새 정책으로 배치해 보고, 한 행이라도 bigone이면 ALTER를 거부. 값은 옮기지 않음 | 명세 109행("ALTER does not relocate")을 그대로 지킴. 두 증상(UPDATE, loaddb) 모두 정확히 막음. 과잉 거부 없음 | 서버 쪽 전체 행 스캔과 배치 시뮬레이션이 새로 필요. ALTER 비용이 테이블 크기에 비례 |
| A2 재작성 | 같은 경우 change mode를 row update로 보내 모든 행을 새 정책으로 다시 씀. 맞지 않는 행이 있으면 ALTER 실패 | 기존 `xlocator_upgrade_instances_domain` 경로 재사용 가능성. `FORCE_INLINE` 컬럼에 stub이 남지 않아 명세 109행의 Open 질문(CBRD-27230)이 사라짐 | 명세 109행 개정 필요. 전체 테이블 재작성과 로그 비용 |
| A3 보수적 검사 | 그 컬럼에 OOS-backed 값이 하나라도 있으면 ALTER 거부 | 규칙이 단순함. stub이 남지 않는 불변식 확보 | 5000B처럼 행 안에 들어갈 값도 거부. 우회는 새 테이블로 복사뿐 |
| C unload 순서 | unloaddb가 `FORCE_INLINE` 을 데이터 적재 뒤(예: index 파일)에 ALTER로 내보냄 | 원본 상태를 그대로 옮김 | unload 형식 변경. schema만 쓰는 사용자는 정책을 잃음. 옮겨진 DB에서도 UPDATE는 계속 실패 |
| D 문서화 | 동작 유지. 명세와 PR 본문에 제한으로 기록, 후속 JIRA | 코드 변경 없음 | 사용자가 정상 DDL로 자기 DB를 unload/load할 수 없는 상태를 만들 수 있음 |
| E loaddb에서 무시 | 적재 때 `FORCE_INLINE` 을 무시하고 demotion | 적재 성공 | 명세 104행 "Never ignore `FORCE_INLINE`" 위반. 제외 |

`heap_object_upgrade_domain` (`heap_file.c:20201`)이 domain이 그대로인 행도 다시 쓰는지는 확인하지 않았습니다. A2의 재사용 가능성은 추정입니다. A1의 구현 규모(대략 100~200줄)도 추정입니다.

## 5. 결과: A1로 이 PR에서 고침 (2026-11-12 확인)

이 보고서를 쓰는 사이 다른 세션이 A1을 구현해 PR에 올렸습니다. 2026-11-12에 작성자가 그대로 유지하기로 했습니다. 한때 D(문서화)를 택했지만, 실제 구현이 예상보다 작다는 것을 확인하고 바꾼 결정입니다.

- 커밋 `87f6f85df3` "[CBRD-27259] Reject an ALTER gaining FORCE_INLINE when an existing row would no longer fit". 7개 파일, 98줄 추가, 14줄 삭제. 기존 `xlocator_upgrade_instances_domain` 에 검사 전용 모드를 더했고, 값은 쓰지 않습니다. 파티션 테이블은 모든 파티션을 검사합니다.
- PR head `19e5d178c` (feature/oos-merge 병합 포함). 이 head의 `github-checks` 실행은 성공했습니다(https://github.com/CUBRID/cubrid/actions/runs/43166076634). gha-ci(sql, shell) 실행 여부는 확인하지 않았습니다.
- 명세 `OOS-CONTEXT.md:109` 에 규칙이 추가돼 있습니다(accepted 2026-11-11).
- PR 본문 rev5(`pr-body-rev5.md:20,24,31`)가 GitHub PR 본문에 반영돼 있습니다.
- 리뷰어 답글이 2026-11-11 13:08Z에 올라가 있습니다(코멘트 id 4538253301). 원문은 `replies.md` 답글 1입니다.

2026-11-12 재측정(공유 install, cub_server 11-12 15:05 설치, 새 코드 포함):

- 20000B 값이 OOS에 있는 행이 있으면 `ALTER ... STORAGE FORCE_INLINE` 이 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (20056 bytes)로 거부되고, 정책은 바뀌지 않습니다. 같은 세션에서 만든 테이블이든 다른 세션이든 같습니다.
- 정책을 `DEFAULT` 로 되돌린 DB는 unloaddb → loaddb에서 1행이 모두 적재됐습니다(`Total 1 object(s) inserted, 0 object(s) failed`).
- 2.3절의 "ALTER 성공" 출력은 2026-11-11 install(`89496263e`) 기준입니다.

### 같은 리뷰의 다른 코멘트와 겹치는 부분

- 4536816663(고정 길이 컬럼만으로 한 페이지를 넘는 스키마를 CREATE/ADD COLUMN이 받아 줌)과 뿌리가 같습니다. 둘 다 "DDL은 성공하고 이후 쓰기가 실패한다"는 문제입니다. 그쪽은 스키마만 보고 판정할 수 있지만, 이쪽은 기존 행을 봐야 한다는 차이가 있습니다.
- 4536816674(REC_BIGONE debug assert)와는 직접 겹치지 않습니다.

## 6. 리뷰어 답변

이미 올라가 있으므로 새 초안은 없습니다. 올라간 답글은 `replies.md` 답글 1을 보세요.

## 7. 확인하지 않은 것

- `87f6f85` 의 코드 리뷰. 커밋 메시지와 diffstat만 읽었습니다.
- CS 모드와 HA 복제에서의 동작. 재현은 모두 SA 모드입니다.
- 파티션 테이블과 하위 클래스에 대한 ALTER.
- 실제 JIRA CBRD-27259의 현재 내용. 로컬 초안만 읽었습니다.
- loaddb 종료 코드와 `--error-control-file` 같은 오류 무시 옵션 사용 시 동작.
- 재현 DB(`srcdb`, `dstdb`)는 `/home/vimkim/tk/rv-alter-force-inline-unload` 에 남겨 두었습니다. 서버는 띄우지 않았습니다(SA 모드).
