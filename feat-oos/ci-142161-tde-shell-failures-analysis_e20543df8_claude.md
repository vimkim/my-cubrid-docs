# CI 142161 (PR #6864 feat/oos) — TDE test_shell 실패 분석 및 수정

- **CI job**: https://app.circleci.com/jobs/github/CUBRID/cubrid/142161 (test_shell, 2026-07-31)
- **CI 엔진 커밋**: `0ad6afc0ff` (feat/oos, develop 머지 직후 — CBRD-27038 미포함)
- **로컬 검증 커밋**: `e20543df8` (branch `feat-oos-fix-regression-TDE`, PR #7588 loaddb fix 포함)
- **TC 브랜치**: `cubrid-testcases-private-ex` `tc/pr-6864` → 수정 브랜치 `tc/pr-6864-tde-fix`
- **작성**: 2026-08-03, Claude (Fable 5)

## 요약 (TL;DR)

CI 142161의 실패 19건 중 TDE 관련 8건(`tbl_enc_08`, `tbl_enc_14`, `file_enc_01~05`, `file_enc_07`)은
**엔진 버그가 아니라 OOS 도입에 따른 물리 레이아웃 변화로 TC 기대값(answer)이 낡은 것**이다.
TDE 암호화 자체는 OOS 파일에 올바르게 적용되고 있음을 로컬에서 검증했다
(OOS 파일 `tde_algorithm: AES`, `file_alloc`↔`pgbuf_set_tde_algorithm(AES)` 쌍 일치,
DROP 시 `file_destroy`가 OOS 페이지의 TDE 비트까지 정리, 리커버리 REDO에서 OOS 페이지 재암호화 확인).
수정은 전부 TC 저장소(answer 8건 + `file_enc_01.sh` anchor 1건)에서 이루어졌고, 로컬에서 8건 모두 OK 전환을 확인했다.

## 왜 실패했는가 — 근본 원인 2가지

### 1. 오버플로 파일(MULTIPAGE_OBJECT_HEAP)이 OOS 파일로 대체됨 — `tbl_enc_08`, `tbl_enc_14`

두 TC는 `encrypt` 테이블에 20,000B varchar를 넣고 `cubrid diagdb -d1` 출력에서
`MULTIPAGE_OBJECT_HEAP` + `Overflow for HFID` 항목이 `tde_algorithm: AES`인지 확인한다.

- **AS-IS(develop)**: ~20KB 레코드 > `heap_Maxslotted_reclength` → `REC_BIGONE` → 오버플로 파일 생성.
- **TO-BE(feat/oos)**: varchar 값이 OOS inline target(16K 페이지 기준 4,060B) 초과 → OOS demotion →
  힙 레코드는 16B OOS inline stub만 보유, 오버플로 파일은 생성되지 않고 `FILE_OOS` 파일이 생성된다.

CI 시점(`0ad6afc`)에는 CBRD-27038(OOS 파일 owner descriptor, PR #7539)이 없어 diagdb에서 OOS 파일이
클래스에 귀속되어 보이지 않았고 result.log에서 항목이 통째로 사라졌다. 현재 HEAD에서는
`CLASS_OID: ... (dba.ttt), OOS for HFID: ...` + `type = OUT_OF_LINE_OVERFLOW_STORAGE` +
`tde_algorithm: AES`로 출력된다 → answer를 이 형태로 갱신.

### 2. 4K 페이지 TC의 "1행 = 1페이지" 가정 붕괴 — `file_enc_01~05`, `file_enc_07`

`file_enc_*`는 `--db-page-size=4K` DB에서 `char(2000)` 5행을 넣어 "행마다 힙 페이지 1장"이 되는
레이아웃을 전제로 er 로그의 TDE 디버그 라인 수열(`file_apply_tde_algorithm`, `pgbuf_set_tde_algorithm`,
`file_alloc`, `pgbuf_dealloc_page`, `file_destroy`)을 answer와 비교한다 (CBRD-26663 때 한 차례 재보정된 TC).

4K 페이지에서 OOS inline target은 약 1KB이므로 char(2000) 값은 전부 OOS로 demotion 된다:

- 힙 파일: 5행의 stub가 한 페이지에 들어가 **초기 5 user pages에서 성장하지 않음**
  (develop은 5행 삽입 후 9 user pages).
- OOS 파일: 값당 1페이지씩 `file_alloc` + `pgbuf_set_tde_algorithm(AES)` 쌍이 추가로 발생.
- DROP TABLE: 힙 + OOS 파일 각각 `file_destroy` → dealloc/clear 라인 수 증가 (`file_enc_03/05`).
- 리커버리(`file_enc_07`): OOS 페이지 포함 `RVPGBUF_SET_TDE_ALGORITHM` REDO 정상 (part 1 OK).

`file_enc_01`만 answer 갱신으로 부족했다. develop의 bestspace 재설계(CBRD-26176, PR #7353) TC 후속
수정(#3529)이 grep anchor를 `pages = 9, tde algorithm = NONE`으로 바꿔놨는데, feat/oos에서는 힙이
5페이지에 머물러 DROP 시 apply가 `pages = 5`를 찍는다 → anchor 불일치 → result.log가 **빈 파일**이 되어
전체 answer가 미스매치. anchor를 `pages = 5`로 되돌리고(OOS 사유 주석 추가) answer를 12줄로 재생성.

참고: `pages = 5`는 develop과 feat/oos가 동일한 초기 힙 할당(5 user pages)을 갖는다는 뜻이며,
차이는 오직 "행이 힙을 성장시키느냐"뿐이다. 즉 PR #7353 동작의 회귀가 아니다.

## 검증 근거 (로컬, debug 빌드 `11.5.0.2484-e20543d`)

- `tbl_enc_08` 재현: diagdb에 힙(AES) + OOS(`OUT_OF_LINE_OVERFLOW_STORAGE`, AES) 출력 확인.
- `tbl_enc_14`: BTREE(AES), 힙(AES), OOS(AES), BTREE_OVERFLOW_KEY(AES) 4파일 모두 확인
  (B-tree overflow key 파일은 OOS와 무관하게 유지됨).
- `file_enc_01` 수동 재현(fe01.err): CREATE 시 `apply(heap, 5p, AES)`,
  첫 INSERT 시 OOS 파일 lazy-create → `apply(oos, 1p, AES)` + 이후 값마다 `file_alloc`+`set AES`,
  DROP 시 `file_destroy(oos, 6p AES 정리)` + `apply(heap, 5p, NONE)`, 재CREATE 시 `apply(heap, 5p, AES)`.
  → CBRD-26830(TDE-on-OOS: walker + lazy-create) 정상 동작 증거.
- 8개 TC 모두 CTP(`ctp.sh shell`)로 재실행하여 [OK] 확인 (아래 수정 내역 참조).

## 수정 내역 (tc/pr-6864-tde-fix)

| TC | 수정 | 내용 |
|---|---|---|
| tbl_enc_08 | answer | MULTIPAGE_OBJECT_HEAP/Overflow 항목 → OUT_OF_LINE_OVERFLOW_STORAGE/OOS for HFID (AES) |
| tbl_enc_14 | answer | 상동 (BTREE_OVERFLOW_KEY 항목은 유지) |
| file_enc_01 | script + answer | grep anchor `pages = 9` → `pages = 5` (OOS 주석 추가), answer 20줄 → 12줄 |
| file_enc_02 | answer | OOS 파일 페이지의 `file_alloc`+`set AES` 쌍 1개 추가 |
| file_enc_03 | answer | AES set 1줄 추가, 첫 file_destroy의 dealloc 1줄 추가 (힙+OOS 2회 destroy 유지) |
| file_enc_04 | answer | OOS lazy-create apply(AES) 블록 추가, 마지막 apply(NONE) set 9→5줄 |
| file_enc_05 | answer | dealloc 9→11줄, set NONE 9→11줄 (dealloc 수 == NONE set 수 의도 유지) |
| file_enc_07 | answer | AES set 8→6줄 (정상 처리 + 리커버리 각 3페이지) |

## 비-TDE 실패 후속 분석 (2026-08-03, 동일 세션)

TC 브랜치 `tc/pr-6864`에 푸시된 커밋: `e7e87aa43`(TDE 8건), `c3a318e6f`(cbrd_26527),
`876639d8d`+`19082d837`(bug_bts_9836/14120 + 잔여물 정리).

### TC 수정으로 해결 (로컬 OK 확인)

- `cbrd_26527` case 4: "오버플로 → OOS" 레이아웃 변화. case 4를 OOS 파일의 `OOS for HFID`
  descriptor 라인(CBRD-27038) 기준으로 재작성 — DROP 후 테이블 소유 2차 저장 파일 회수 검증 의도 유지.
- `bug_bts_9836`, `bug_bts_14120`: feat/oos 가 `call_stack_dump_error_codes` 기본 목록에
  `ER_HEAP_OOS_BAD_INLINE_HEADER(-1378)`, `ER_HEAP_OOS_CORRUPTED_RECORD(-1380)`,
  `ER_HEAP_OOS_INVALID_ARGUMENT(-1381)` 를 추가 → paramdump 기본 activation list에 `-50` 뒤로
  세 코드가 출현. answer 갱신.

### 엔진(#7588)으로 이미 해결된 것 (로컬 OK 확인)

- `bug_xdbms_sus880`, `itrack_10006`: CI 빌드(`0ad6afc`)에 PR #7588(loaddb MVCCID self-lock)
  미포함으로 인한 서버 abort. `e20543d` 빌드에서 통과.
- `cbrd_27064`(CDC overflow-UPDATE): 로컬 통과 — CI 커밋 이후 develop 머지로 엔진 fix 유입 추정.

### 신규 엔진 결함 발견 (TC로 해결 불가 — JIRA 필요)

1. **`cbrd_23430`: cub_server assert in `pgbuf_fix_debug` (page_buffer.c:2564)**
   server-side loaddb의 OOS insert 중 `file_alloc`(NEW_PAGE)이 돌려준 페이지(0|12690)의 버퍼가
   이미 초기화된 **dirty PAGE_FTAB** 페이지. 그 FTAB 페이지의 LSA(4338|7768)는 재시작 시점
   append_lsa(173|12400)보다 훨씬 이후 → **현재 loaddb가 만든 OOS 파일(0|12352) 자신의 파일
   테이블 페이지를 user page로 이중 배정**한 것 (recovery 잔재 아님, 단일 loaddb worker 스레드).
   의심 지점: numerable OOS 파일의 user-page-table/FTAB 확장 시 partial-sector 비트 누락.
   release 빌드는 f_init 재초기화로 은폐되나 debug/optdebug(CI)에서 abort.
   증거: core `core.loaddb.631552`(ERROR_BACKUP `AUTO_...193122.tar.gz`), 스택 oos_insert_many →
   oos_find_best_page → oos_file_alloc_new → file_alloc.
2. **`cbrd_27075`: cub_server assert in `oos_check_head_header` (oos_file.cpp:1681)**
   CDC 로그 추출(`cdc_make_dml_loginfo`)이 UPDATE undo recdes의 OOS inline stub을
   `heap_attrvalue_read_oos_inline` → `oos_read`(expected_length=40968)로 Resolve하다 헤더
   불일치 assert. CDC는 로그를 비동기로 읽으므로 그 시점에 vacuum이 old value chain을 이미
   삭제/슬롯 재사용했을 수 있음 — CBRD-26950(ANCHORED 슬롯 재사용)과 "CDC flashback OOS-stub
   Resolve 미구현" 갭의 교차점. release 빌드에선 CDC가 오염된 before-image를 출력할 위험.
   증거: core `core.cdc-loginfo-pro.715349`(ERROR_BACKUP `AUTO_...194320`).

### 미결 (본 세션 진행 중)

- `bigPageSize`: #7588로 loaddb는 성공하나 16K→4K loaddb 후 SELECT 결과가 원본과 diff.
- `cbrd_25365`(아카이브 로그 타이밍), `cbrd_25481`(unloaddb/loaddb 대형 행): 로컬 재실행으로 판별 중.
