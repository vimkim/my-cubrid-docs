# CBRD-27350 — `spacedb` / `diagdb` OOS 관측성 현재 상태와 잔여 범위

> 조사일: 2026-09-01  
> 기준 소스: `bd0766dbb8e7e1d5f1f6f87824aa8819233991e9` (`cbrd-26786-oos-page-clean`)  
> 대상 JIRA: [CBRD-27350](http://jira.cubrid.org/browse/CBRD-27350)  
> 조사 성격: 이슈 작성 전 current-state gap analysis. JIRA/소스 수정, commit, push는 하지 않았다.

## 결론

CBRD-27350을 현재 코멘트의 **T1 + T2 + `diagdb` + release 관측성** 묶음으로 구현하면 이미 끝난 일을
중복한다. 2026-09-01 현재 상태는 다음과 같다.

| 원래 주장/범위 | 현재 판정 | 근거 |
|---|---|---|
| `diagdb`가 OOS 파일을 표시하지 못한다 | **완료, 주장 자체가 인용한 PR 리뷰 시점에도 이미 stale** | CBRD-27038 commit `0c0e6f32c`가 OOS owner descriptor와 `CLASS_OID ..., OOS for HFID ...` 출력을 추가했다. 이 commit은 리뷰 대상 `66cd3cc`의 ancestor다. 현재 `diagdb -d2`는 모든 파일의 type, user-page 수, descriptor를 출력한다. [S4][S6][S7] |
| T2: OOS descriptor에 parent HFID/class OID 저장 | **완료** | `FILE_OOS_DES { HFID hfid; OID class_oid; }`, lazy create 시 두 필드 저장, file tracker가 class lock으로 OOS를 보호한다. CBRD-27038은 Resolved/Fixed다. [S4][S5] |
| release build에서는 OOS 발동/페이지 수를 알 수 없고 debug `oos.log`만 가능 | **완료/대체됨** | CBRD-26972의 DBA 전용 `SHOW HEAP OOS OF <class>`가 OOS 존재, VFID, 정확한 allocated user-page 수, record/byte 통계를 SQL result set으로 반환한다. debug guard가 없다. CBRD-26972는 Resolved/Fixed다. [S3][S8][S9] |
| CBRD-26786 CTP page-reclaim A/C가 CBRD-27350에 의존한다 | **의존하지 않음** | 격리된 test table에서 `SHOW HEAP OOS OF t`의 `Has_oos_file`과 `Oos_num_user_pages`를 cycle 전후 비교하면 release build에서 OOS 발동과 page-count 안정성을 검증할 수 있다. `Oos_num_user_pages`는 `file_get_num_user_pages()`에서 직접 읽는다. [S8][S9] |
| `spacedb`가 OOS 공간을 전혀 세지 않는다 | **틀림** | CBRD-27028 이후 `FILE_OOS`의 file/page/reserved 값을 `SPACEDB_HEAP_FILE`에 합산한다. 즉 전체/HEAP totals에는 포함되지만 OOS만 분리할 수 없다. [S2][S10] |
| T1: `SPACEDB_OOS_FILE` 별도 category | **유일한 잔여 gap** | 현재 enum은 INDEX/HEAP/SYSTEM/TEMP/TOTAL뿐이고 `FILE_OOS`는 명시적으로 HEAP에 fold된다. [S10][S11] |

따라서 권장 처리는 다음 둘 중 하나다.

1. **별도 OOS global accounting이 제품 요구라면 이슈를 T1 하나로 재범위화한다.** 제목은 예를 들어
   `[OOS] Add a separate OOS category to cubrid spacedb -p`가 정확하다. 우선순위는 Minor가 적절하며,
   CBRD-26786 merge gate의 prerequisite로 표현하지 않는다.
2. **`spacedb -p`의 별도 global row를 실제 소비하는 DBA/QA 요구가 없다면 close한다.** `diagdb`/owner는
   CBRD-27038, per-table release 관측은 CBRD-26972, safe utility handling과 HEAP 합산은 CBRD-27028이 이미
   충족한다.

이 보고서는 1번을 위한 좁은 issue-writing foundation을 아래에 제공한다. **per-table attribution을
`spacedb`에 다시 구현하지 않는다.** 그 목적에는 이미 `SHOW HEAP OOS`가 더 정확한 interface다.

## 왜 기존 근거가 stale인가

### 시간 순서

| 날짜 | 사건 | 현재 의미 |
|---|---|---|
| 2026-07-13 | CBRD-27028 / `8b209ee3c`: utility assert 제거, OOS를 `SPACEDB_HEAP_FILE`에 합산 | `spacedb` abort/누락 문제 해결; 별도 OOS category만 보류 [S2] |
| 2026-07-22 | CBRD-26972 / `fae01b05d`: `SHOW HEAP OOS` 진단 SQL 추가 | release-build per-table OOS 관측 수단 확보 [S3][S8] |
| 2026-07-31 | CBRD-27038 / `0c0e6f32c`: owner HFID/class OID, `diagdb`, protected tracker | T2 및 `diagdb` 범위 완료 [S4][S5] |
| 2026-08-14 | PR #7617 리뷰 대상 `66cd3cc` 생성 | 위 세 commit을 모두 포함 [S6] |
| 2026-08-21 | H2SU review `4991862087`: `spacedb`/`diagdb`에서 OOS가 보이지 않는다고 기록 | 해당 binary/source와 불일치하는 side finding [S6] |
| 2026-09-01 | CBRD-27350 생성, 같은 review와 구 CBRD-26871 T1/T2를 근거로 priority 상향 요청 | CBRD-26972/27038을 반영하지 않은 설명 [S1] |

`git merge-base --is-ancestor`로 `8b209ee3c`, `fae01b05d`, `0c0e6f32c`가 모두 리뷰 대상
`66cd3ccc564e50107b04cfe60770c00c53756ec3`의 ancestor임을 확인했다. 따라서 review의 **SA leak 실측**은
CBRD-26786에 유효한 중요한 증거지만, 같은 review의 **관측성 side finding**은 그 binary의 실제 기능을
설명하지 못한다. [S6]

리뷰 commit부터 현재 `bd0766dbb`까지의 CBRD-26786 후속 patch도 대조했다. 이 구간은 empty-page reclaim,
growth-gate sweep, LSA gate, stale VPID 방어와 관련 test를 강화했지만 `SPACEDB_FILE_TYPE`,
`file_tracker_item_spacedb()`, `spacedb` output labels, `SHOW HEAP OOS` schema, OOS descriptor 출력의 의미는
바꾸지 않았다. 현재 HEAD에서도 `FILE_OOS -> SPACEDB_HEAP_FILE` mapping이 그대로이므로 잔여 gap 판정은
최신 CBRD-26786 patch 전체를 포함한다. [S10][S11]

### 로컬 문서의 유효 범위

`my-cubrid-docs/cbrd-26786/PR-7617-H2SU-sa-leak-explainer_8ba9b5398_claude.md`와
`PR-7617-reviewer-comments-validity-report_66cd3cc_claude.md`는 SA mode에서 15KB × 14,000행
delete/reinsert 시 320→640→768→1024MB로 성장했다는 재현 및 성장-gate sweep 도입 이유를 잘 보존한다.
이 자료는 **누수 문제와 재현 workload의 1차 보조 증거**로 계속 유효하다. 다만 문서의
"release에서는 `oos.log`만 가능" 및 "`diagdb`가 OOS를 못 본다"는 관측성 결론은 CBRD-26972/27038을
누락했으므로 현재 이슈 범위의 근거로 재사용하면 안 된다. [S12]

OOS normative context의 Known Bugs 표도 같은 stale statement를 담고 있다
(`/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:442`): owner metadata 부재, unprotected tracker,
release 관측 수단 부재를 아직 현재형으로 기술한다. 이것은 required OOS invariant가 아니라 dated
implementation-status 설명이며, current source/JIRA와 충돌하므로 후속 문서 정정 대상이다. [S13]

## Current implementation

### 1. OOS owner metadata와 `diagdb`: DONE

현재 OOS descriptor는 별도 type이다.

```text
FILE_OOS_DES
  hfid       -> owner heap HFID
  class_oid  -> owner class OID
```

- `oos_create_file()`은 lazy create 시 `des.heap_oos.hfid`와 `des.heap_oos.class_oid`를 채운다
  (`src/storage/oos_file.cpp:1227-1228 @ bd0766dbb`).
- `file_header_dump_descriptor(FILE_OOS)`는 class name/OID와
  `OOS for HFID: <volid>|<fileid>|<hpgid>`를 출력한다
  (`src/storage/file_manager.c:1424-1434 @ bd0766dbb`).
- interruptible tracker는 `descriptor.heap_oos.class_oid`로 class conditional lock을 잡고 OOS file을
  안전하게 반환한다 (`file_tracker_get_and_protect`, `src/storage/file_manager.c:10882-11002`).
- `diagdb`의 `DIAGDUMP_FILE_CAPACITIES`는 값 2이며, `file_tracker_dump_all_capacities()`를 호출한다
  (`src/executables/util_sa.c:1499-1505,1620-1625`). 이 scanner는 모든 tracked file에 대해 VFID,
  `n_page_user`, file type, descriptor를 출력한다
  (`src/storage/file_manager.c:11221-11287`).
- `diagdb`는 `SA_ONLY` utility다 (`src/executables/util_admin.c:981`). 즉 offline 상세 진단은 가능하지만
  online global summary interface는 아니다. [S5][S7]

결론: CBRD-27350에서 owner descriptor, `diagdb` 출력, online checkdb protection을 다시 다루지 않는다.

### 2. Per-table/release observability: DONE by `SHOW HEAP OOS`

CBRD-26972가 다음 DBA 전용 SQL을 추가했다.

```sql
SHOW HEAP OOS OF <class>;
SHOW ALL HEAP OOS OF <class>;
```

주요 결과는 `Has_oos_file`, `Oos_volume_id`, `Oos_file_id`, `Oos_num_user_pages`, `Oos_num_recs`,
`Oos_physical_bytes`, `Oos_unused_bytes`다 (`src/parser/show_meta.c:385-420`). parser와 SHOW scan dispatch에
일반 기능으로 등록되어 있고 NDEBUG/debug 조건부가 아니다
(`src/parser/csql_grammar.y:7550-7556`, `src/query/show_scan.c:173-183`). [S8]

`Oos_num_user_pages`의 신뢰 범위는 record count와 구분해야 한다.

- **Allocated page count는 file header 기반**: `oos_get_stats_by_vfid()`가
  `file_get_num_user_pages()` 결과를 그대로 저장한다 (`src/storage/oos_file.cpp:3422-3428`). CBRD-26786의
  file growth/reclaim trend 검증에 적합하다.
- **Live record/record-byte count는 진단 snapshot**: data-page read latch가 바쁘거나 concurrent dealloc이면
  해당 page를 skip하므로 순간적인 undercount가 가능하다 (`src/storage/oos_file.cpp:3440-3484`). 정확한
  transactional accounting으로 취급하지 않는다.
- SQL scan은 위 page count로 `Oos_physical_bytes = num_user_pages * DB_PAGESIZE`를 만든다
  (`src/storage/heap_oos.cpp:849-935`). [S9]

따라서 CBRD-26786 release CTP는 isolated table에서 다음처럼 구성할 수 있다.

```sql
SHOW HEAP OOS OF t_reclaim;
-- Has_oos_file = 1: OOS file 생성/발동 증거
-- Oos_num_user_pages: delete+reinsert cycle 사이 allocated page count 비교
```

한 table만 쓰고 비압축 `BIT VARYING` test data를 사용하면 다른 table의 OOS file과 섞이지 않는다.
이는 global `spacedb` category보다 CBRD-26786의 per-table page-reclaim A/C에 더 직접적이다.

### 3. `spacedb`: counted, but not separated

`cubrid spacedb -p`의 현재 file-type model은 다음 다섯 출력 row다.

```text
INDEX, HEAP, SYSTEM, TEMP, TOTAL
```

- enum에는 `SPACEDB_OOS_FILE`이 없다 (`src/storage/storage_common.h:579-589`).
- `file_tracker_item_spacedb()`는 `FILE_OOS`의 `nfile`, `n_page_user`, `n_page_ftab`, `n_page_free`를
  `SPACEDB_HEAP_FILE` bucket에 합산한다 (`src/storage/file_manager.c:12226-12275`).
- client output label도 `"INDEX", "HEAP", "SYSTEM", "TEMP", "-"`로 고정되고 category 전부를 순회한다
  (`src/executables/util_cs.c:944-957,1140-1168`).
- `spacedb`는 SA/CS 모두 지원하고, `-p`/`--purpose`일 때만 detailed file usage를 요청한다
  (`src/executables/util_admin.c:247-264,976`; `src/executables/util_cs.c:1045-1056`). [S10][S11]

그러므로 현재 문제를 정확히 쓰면 다음 한 문장이다.

> `cubrid spacedb -p`의 HEAP row에는 OOS file space가 포함되지만 heap 본체와 OOS를 구분할 수 없어,
> online/standalone global accounting에서 OOS 총량만 따로 추세화할 수 없다.

"OOS pages are missing from spacedb" 또는 "spacedb aborts on FILE_OOS"는 현재 상태가 아니다.

## 재범위화할 경우의 Issue Triage 초안

### 목적

`cubrid spacedb -p`에 별도 `OOS` file category를 추가하여, DBA가 전체 database에서 OOS file의 수와
user/file-table/reserved page 사용량을 heap 본체와 분리해 확인할 수 있게 한다.

### 이유

**AS-IS:** CBRD-27028 이후 `FILE_OOS` space는 누락되지 않고 `HEAP` row에 합산된다. 따라서 total
accounting은 맞지만, OOS와 heap 본체가 섞여 있어 database-wide OOS growth/reclaim 추세를 `spacedb` 한
명령으로 분리할 수 없다. Per-table OOS는 CBRD-26972의 `SHOW HEAP OOS`, offline owner 진단은
CBRD-27038의 `diagdb -d2`가 이미 제공한다.

**TO-BE:** `cubrid spacedb -p`가 `OOS` row를 별도로 출력하고, 기존 `HEAP` row는 heap/heap-overflow만
집계한다. `TOTAL`은 변경 전과 동일해야 한다. SA/CS mode 모두 같은 값을 보여야 한다.

**영향:** DBA/QA가 database-wide OOS allocation을 heap 본체와 분리해 관찰할 수 있다. 다만
CBRD-26786의 per-table release test gate는 이미 `SHOW HEAP OOS`로 충족되므로 이 이슈는 merge
prerequisite가 아니라 독립적인 Minor observability enhancement다.

### 방안

1. `SPACEDB_FILE_TYPE`에 `SPACEDB_OOS_FILE`을 추가하고 `FILE_OOS`를 새 bucket으로 mapping한다.
2. `spacedb -p` client label에 `OOS`를 추가한다.
3. server pack/client unpack의 category count 및 response size를 함께 갱신한다.
4. HEAP에서 빠진 수치가 OOS로 이동했을 뿐 TOTAL은 동일함을 SA/CS test로 검증한다.
5. 기존 `SHOW HEAP OOS`, `diagdb`, owner descriptor에는 변경을 가하지 않는다.

## Candidate Acceptance Criteria

- [ ] `cubrid spacedb -p --size-unit=page`가 `INDEX`, `HEAP`, `OOS`, `SYSTEM`, `TEMP`, `TOTAL`을 출력한다.
- [ ] OOS file이 없는 database에서 `OOS` row의 file/user/ftab/reserved 값은 모두 0이다.
- [ ] isolated OOS table을 만든 뒤 `OOS.nfile >= 1`, `OOS.user_pages > 0`이고 같은 수치가 더 이상
      `HEAP` row에 포함되지 않는다.
- [ ] 변경 전 `HEAP`에 포함되던 OOS 수치가 변경 후 `OOS`로 정확히 이동하며, 각 column의 `TOTAL`은
      변하지 않는다.
- [ ] `spacedb -S -p`와 `spacedb -C -p`가 동일 database에 대해 같은 category 값을 반환한다.
- [ ] size unit `page`, `m`, `g`, `t`, `h`에서 새 row가 기존 format과 동일하게 출력된다.
- [ ] OOS insert → delete/reclaim → reinsert workload에서 `OOS` row가 실제 allocated-file-page 변화를
      반영한다. Per-table 판정은 같은 시점의 `SHOW HEAP OOS OF <class>`와 교차 확인한다.
- [ ] 기존 `diagdb -d2` owner 출력과 `SHOW HEAP OOS` 결과 schema가 바뀌지 않는다.
- [ ] 관련 utility answer/golden files와 C/S serialization tests가 갱신된다.

## Candidate tests

| Test | 핵심 검증 |
|---|---|
| No-OOS baseline | 새 `OOS` row가 0이며 TOTAL 회계가 유지됨 |
| One OOS table | `SHOW HEAP OOS`의 OOS VFID/page 존재와 `spacedb -p` OOS global count가 함께 증가 |
| Two OOS tables | OOS global `nfile` 증가, table별 값은 각각 `SHOW HEAP OOS`로 확인 |
| Drop one table | OOS global `nfile`/pages 감소, 남은 table 통계 보존 |
| CBRD-26786 churn | 15KB `BIT VARYING` × 14,000행 delete/reinsert 반복 시 per-table page count flat; global OOS row도 수렴 |
| SA/CS parity | 같은 DB에 `-S -p`와 `-C -p`를 실행해 row/값 비교 |
| Packing round trip | `or_packed_spacedb_size`, `or_pack_spacedb`, `or_unpack_spacedb`가 새 count를 동일하게 처리 |

## Compatibility and risks

### Client/server response shape

`SPACEDB_FILE_COUNT`는 단순 display constant가 아니다.

- server는 `SPACEDB_FILES files[SPACEDB_FILE_COUNT]`를 만들고
  (`src/communication/network_interface_sr.cpp:10775-10830`),
- pack size와 body는 category당 4개 integer를 보낸다
  (`src/object/object_representation.c:6117-6143,6158-6193`),
- client는 자기 `SPACEDB_FILE_COUNT`만큼 unpack한다
  (`src/object/object_representation.c:6209-6277`; `src/communication/network_interface_cl.c:10895-10939`).

따라서 enum 하나 추가는 **wire response length와 CLI output을 함께 바꾸는 변경**이다. 같은-version
server/client만 지원한다면 양쪽을 동시에 변경하면 된다. 구 client↔신 server 또는 신 client↔구 server의
cross-version 관리 utility compatibility를 보장해야 한다면 count/version negotiation 또는 별도 optional
field가 필요하다. 현재 코드에는 category count가 payload 안에 없으므로 이 결정을 명시해야 한다. [S14]

### Output compatibility

`spacedb -p`는 category를 전부 항상 출력한다. `OOS` row 추가는 OOS가 없는 DB에서도 한 줄의 output
drift를 만든다. 기존 shell answer와 output parser가 5-row 구조를 가정하는지 검색하고 갱신해야 한다.

### Accounting semantics

- `spacedb`의 `OOS`는 **database-wide allocated file/page accounting**이다.
- `SHOW HEAP OOS`는 **class-scoped OOS 진단**이다.
- `diagdb -d2`는 **offline file descriptor/capacity dump**다.

세 interface를 하나의 scope로 합치지 않는다. 특히 `spacedb`에 table name/HFID별 rows를 억지로 넣으면
현재 fixed-category protocol을 넘는 별도 data model/API가 필요하고 `SHOW HEAP OOS`와 중복된다.

## Open decisions

1. **별도 global OOS row를 실제로 요구하는 consumer가 있는가?** 없다면 CBRD-27350은 superseded로
   close하는 편이 낫다.
2. **`spacedb -p` output drift를 허용하는가?** OOS가 없어도 `OOS 0 0 0 0` row가 생긴다.
3. **cross-version C/S compatibility가 요구되는가?** 요구되면 단순 enum/count 증가는 부족하다.
4. **HEAP의 의미를 바꿔도 되는가?** TO-BE에서 HEAP는 OOS를 제외한다. 기존 monitoring이 HEAP row를
   "table-owned total"로 해석했다면 값이 감소한다. 호환성을 우선하면 HEAP를 유지하면서 OOS를 중복 표시할
   수도 있지만 TOTAL double-count 방지와 label semantics가 혼란스러워 권장하지 않는다.
5. **CBRD-26786 CTP를 별도로 갱신할 것인가?** 권장: 이 이슈와 무관하게 `SHOW HEAP OOS` 기반 release
   assertion으로 바꾼다. CBRD-27350을 기다릴 이유가 없다.

## Recommended disposition

현재처럼 "spacedb / diagdb with OOS"와 T1/T2를 함께 쓰지 않는다.

- **Keep + re-scope**: global OOS/HEAP split이 명시적으로 필요하면 T1만 남기고 위 A/C로 작성한다.
- **Close as superseded**: 목적이 release observability, per-table attribution, `diagdb`, CBRD-26786 test gate
  해소였다면 CBRD-26972 + CBRD-27028 + CBRD-27038이 이미 충족했다.

현재 증거만으로는 global OOS row의 명시적 consumer가 확인되지 않는다. 따라서 구현 전 담당자가 1번 open
decision만 답하면 된다. "이 이슈를 반드시 유지한다"가 팀 결정이라면 **T1-only로 재범위화**하는 것이 가장
작고 검증 가능한 형태다.

## Sources

- **[S1] Current JIRA:** `cubrid-jira search CBRD-27350`, fetched 2026-09-01; Open/Minor, description 없음,
  comment가 T1+T2 및 PR #7617 dependency를 주장. Cache:
  `/home/vimkim/.local/share/cubrid-jira/issues/CBRD-27350.md:1-36`.
- **[S2] CBRD-27028:** [JIRA](http://jira.cubrid.org/browse/CBRD-27028), Resolved/Fixed;
  commit `8b209ee3c255e8ae8f4cb2694bda353b8979935a` (`Handle FILE_OOS asserts in utilities`). Commit message와
  diff가 OOS→HEAP fold를 output/protocol 안정성 선택으로 명시한다.
- **[S3] CBRD-26972:** [JIRA](http://jira.cubrid.org/browse/CBRD-26972), Resolved/Fixed;
  commit `fae01b05dfb9114c201e912adcc0aa8b358857f0` (`Add SHOW HEAP OOS diagnostics`).
- **[S4] CBRD-27038:** [JIRA](http://jira.cubrid.org/browse/CBRD-27038), Resolved/Fixed;
  commit `0c0e6f32cc2be6c4a92380d2bc23cc147e6977dc` (`Add OOS file owner metadata`). 상세 검증 문서:
  `/home/vimkim/gh/my-cubrid-docs/cbrd-27038/CBRD-27038-oos-owner-descriptor_59607e6_codex.md`.
- **[S5] Current owner/diag source @ `bd0766dbb`:**
  `src/storage/file_manager.h:98-104,136-146`; `src/storage/oos_file.cpp:1221-1231`;
  `src/storage/file_manager.c:1424-1434,10882-11002,11221-11287`;
  `unit_tests/oos/test_oos_server.cpp:250-330`.
- **[S6] PR review:** [H2SU review 4991862087](https://github.com/CUBRID/cubrid/pull/7617#pullrequestreview-4991862087),
  submitted 2026-08-21 against `66cd3ccc564e50107b04cfe60770c00c53756ec3`. Local git ancestry check confirms
  S2/S3/S4 commits are all ancestors of that review commit.
- **[S7] `diagdb` path @ `bd0766dbb`:** `src/executables/util_admin.c:968-984`;
  `src/executables/util_sa.c:1499-1505,1620-1625`; `src/storage/file_manager.c:11221-11287`.
- **[S8] SHOW SQL @ `bd0766dbb`:** `src/parser/csql_grammar.y:7538-7557`;
  `src/parser/show_meta.c:385-420`; `src/query/show_scan.c:173-183`;
  `unit_tests/oos/sql/test_oos_sql_show.cpp:180-350`.
- **[S9] SHOW stats @ `bd0766dbb`:** `src/storage/heap_oos.cpp:793-947`;
  `src/storage/oos_file.cpp:3405-3486`; `src/storage/oos_file.hpp:142-154`.
- **[S10] Current spacedb accounting @ `bd0766dbb`:**
  `src/storage/file_manager.c:12226-12317`; `src/storage/storage_common.h:579-598`.
- **[S11] `spacedb -p` client/output @ `bd0766dbb`:** `src/executables/util_admin.c:247-264,976`;
  `src/executables/util_cs.c:944-957,1045-1056,1140-1168`.
- **[S12] CBRD-26786 local evidence:**
  `/home/vimkim/gh/my-cubrid-docs/cbrd-26786/PR-7617-H2SU-sa-leak-explainer_8ba9b5398_claude.md`;
  `/home/vimkim/gh/my-cubrid-docs/cbrd-26786/PR-7617-reviewer-comments-validity-report_66cd3cc_claude.md`.
- **[S13] Normative OOS context:**
  `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md:1-18,431-442` (last-updated marker 2026-08-28;
  line 442 implementation-status statement conflicts with S2-S5/S8-S9).
- **[S14] spacedb serialization @ `bd0766dbb`:**
  `src/object/object_representation.c:6108-6281`;
  `src/communication/network_interface_sr.cpp:10765-10845`;
  `src/communication/network_interface_cl.c:10887-10942`.
