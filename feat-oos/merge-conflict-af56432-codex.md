# `feat/oos`–`develop` 병합 충돌 해결 보고서

## 1. 개요

본 보고서는 `feat/oos`에서 `origin/develop`을 병합하면서 발생한 충돌의 원인, 사용자 검토를 거친 해결 결정, 그리고 검증 결과를 기록합니다.

| 항목 | 값 |
|---|---|
| 작업 브랜치 | `feat/oos` |
| OOS 측 부모 | `07fef9d48b4776e60c42e8afa25b9f21c54b8226` |
| 병합한 `develop` 커밋 | `af56432c507de2ac9b7b56730297d69259430d63` |
| merge base | `11f0140a984bbdc05f66ad5061f0ddf282e5a130` |
| merge commit | `dee68b1f46d38705d1d1068547884f68570a818f` |
| 해결일 | 2026-08-12 |
| 텍스트 conflict chunk | 6개 파일에 각 1개, 총 6개 |
| 테스트가 발견한 의미 충돌 | 1개 |

merge base 이후 OOS 측에는 91개, `develop` 측에는 28개의 고유 커밋이 있었습니다.

## 2. 결론

모든 충돌에는 사용자가 확정한 다음 우선순위를 적용했습니다.

> `develop` 변경을 먼저 유지하고, OOS 전용 번호와 항목은 항상 그 아래에 배치한다.

이 원칙은 단순히 `theirs`를 선택한다는 뜻이 아닙니다. `develop`이 새로 확보한 공개 번호와 순서를 먼저 보존하고, OOS 동작에 필요한 변경은 그 뒤의 새 번호 또는 새 위치로 이동하여 두 의도를 모두 유지한다는 뜻입니다.

최종 결과는 다음과 같습니다.

1. `develop`의 no-logging index 오류 및 recovery index를 원래 번호 1377과 133~134에 유지했습니다.
2. `feat/oos`의 오류 코드는 그 아래 1378~1382로, recovery index는 135~141로 이동했습니다.
3. `develop`의 `heap_rv_mvcc_redo_insert` stack-use-after-scope 수정과 OOS의 record flag 분리를 동시에 보존했습니다.
4. Git이 감지하지 못한 parser semantic message 번호 충돌까지 테스트로 찾아 해결했습니다.
5. 최종 `debug_gcc` 빌드·설치와 CTest 25개가 모두 성공했습니다.

## 3. 충돌이 발생한 이유

충돌은 크게 세 유형이었습니다.

### 3.1 끝 번호를 양쪽이 독립적으로 사용

공통 조상에서 engine 오류 catalog의 마지막 항목은 1377이었습니다. 이후 양쪽 브랜치가 같은 빈 번호를 독립적으로 사용했습니다.

- `develop`: CBRD-27071 no-logging parallel index build 오류를 1377에 추가
- `feat/oos`: Vacuum daemon 및 OOS 오류를 1377~1381에 추가

영어·한국어 message catalog와 `error_code.h`가 모두 같은 영역을 수정했으므로 세 파일에서 텍스트 충돌이 발생했습니다.

Parser semantic message에서도 같은 형태의 충돌이 있었지만, 양쪽 변경이 인접한 서로 다른 줄에 적용되어 Git은 이를 자동 병합했습니다. 그 결과 338번이 UUID 오류와 OOS STORAGE 오류에 동시에 배정되는 의미 충돌이 남았습니다.

### 3.2 동일 선언부에 서로 독립적인 수정

`heap_rv_mvcc_redo_insert`에서 양쪽이 같은 지역 변수 선언부를 수정했습니다.

- `develop` CBRD-27206: `data_buffer`를 `else` 블록 밖으로 이동해 `RECDES`가 수명이 끝난 스택 버퍼를 참조하지 않도록 수정
- `feat/oos` CBRD-26973: OOS flag까지 포함하는 전체 record flag를 MVCC flag와 구분하도록 `mvcc_flag`를 `record_flags`로 변경

두 변경은 목적이 다르고 서로 양립 가능하지만, 같은 줄을 수정했기 때문에 Git이 자동 결합하지 못했습니다.

### 3.3 위치 기반 recovery table의 동일한 꼬리에 양쪽이 항목 추가

`LOG_RCVINDEX`와 `RV_fun[]`은 enum 값과 배열 위치가 정확히 같아야 합니다. 공통 조상의 마지막 recovery index가 132였고 양쪽이 모두 133부터 새 항목을 추가했습니다.

- `develop`: no-logging index recovery 항목 2개
- `feat/oos`: OOS insert/delete, replication, vacuum 및 forward-delete 항목 7개

양쪽 목록을 단순 연결하거나 번호만 수정하면 `RV_fun[rcvindex]`가 잘못된 handler를 가리킬 수 있으므로 enum과 배열을 하나의 순서로 함께 재구성해야 했습니다.

## 4. 텍스트 conflict chunk별 해결

### 4.1 Chunk 1 — 영어 engine 오류 메시지

대상: `msg/en_US.utf8/cubrid.msg`

`develop`의 no-logging index 오류를 1377에 유지하고, `feat/oos`에서 추가한 오류를 아래로 이동했습니다.

| 번호 | 최종 항목 | 출처 |
|---:|---|---|
| 1377 | no-logging index vacuum notification limit | `develop` |
| 1378 | Vacuum master daemon not available | `feat/oos` |
| 1379 | bad OOS inline header | OOS |
| 1380 | OOS + bigone rejection | OOS |
| 1381 | corrupted OOS record metadata | OOS |
| 1382 | invalid OOS argument | OOS |
| 1383 | `Last Error` | sentinel |

관련 위치: `msg/en_US.utf8/cubrid.msg:1482`

### 4.2 Chunk 2 — 한국어 engine 오류 메시지

대상: `msg/ko_KR.utf8/cubrid.msg`

Chunk 1과 동일한 번호 배치를 적용하여 locale 간 번호와 의미를 일치시켰습니다.

관련 위치: `msg/ko_KR.utf8/cubrid.msg:1481`

### 4.3 Chunk 3 — engine 오류 코드 정의

대상: `src/base/error_code.h`

메시지 catalog와 동일하게 다음 번호를 배정했습니다.

```text
ER_BT_LOAD_NOTIFY_VACUUM_LIMIT          -1377
ER_VACUUM_MASTER_DAEMON_NOT_AVAILABLE   -1378
ER_HEAP_OOS_BAD_INLINE_HEADER           -1379
ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE        -1380
ER_HEAP_OOS_CORRUPTED_RECORD            -1381
ER_HEAP_OOS_INVALID_ARGUMENT            -1382
ER_LAST_ERROR                           -1383
```

이 오류들은 CCI 공개 오류 헤더에 복제되어 있지 않은 engine 내부 오류이므로 `cubrid-cci/src/cci/base_error_code.h`는 변경하지 않았습니다.

관련 위치: `src/base/error_code.h:1772`

### 4.4 Chunk 4 — MVCC redo insert의 버퍼 수명과 record flag

대상: `src/storage/heap_file.c`

해결 결과는 양쪽 변경을 결합한 형태입니다.

```c
char data_buffer[IO_DEFAULT_PAGE_SIZE + OR_MVCC_MAX_HEADER_SIZE + MAX_ALIGNMENT];

/* ... */

else
  {
    int repid_and_flags, offset, record_flags, offset_size;
```

- `data_buffer`는 함수 범위에 두어 `develop`의 stack-use-after-scope 수정을 유지했습니다.
- flag 변수와 추출식은 `record_flags`, `OR_RECORD_FLAG_SHIFT_BITS`, `OR_RECORD_FLAG_MASK`를 사용하여 OOS record flag 분리를 유지했습니다.

관련 위치: `src/storage/heap_file.c:17254`, `src/storage/heap_file.c:17262`, `src/storage/heap_file.c:17294`

### 4.5 Chunk 5 — recovery handler 배열

대상: `src/transaction/recovery.c`

기존 0~132 항목 뒤에 `develop` handler를 먼저 배치하고, OOS handler를 이어 붙였습니다.

```text
133~134  develop no-logging index handlers
135~141  OOS handlers
```

각 OOS handler의 undo/redo/dump 함수는 변경하지 않았습니다. 순서만 enum과 일치하도록 이동했습니다.

관련 위치: `src/transaction/recovery.c:863`, `src/transaction/recovery.c:875`, `src/transaction/recovery.c:915`

### 4.6 Chunk 6 — recovery index enum

대상: `src/transaction/recovery.h`

최종 번호는 다음과 같습니다.

```text
RVBT_NO_LOGGING_INDEX_DURABLE           133
RVBT_NO_LOGGING_INDEX_COMMITTED         134
RVOOS_INSERT                            135
RVOOS_DELETE                            136
RVREPL_OOS_INSERT                       137
RVREPL_OOS_DELETE                       138
RVOOS_NOTIFY_VACUUM                     139
RVREPL_DUMMY_OOS_RECORD                 140
RVHF_DELETE_NEWHOME_NOTIFY_VACUUM       141
RV_LAST_LOGID                           141
```

OOS 번호는 최신 `develop` recovery index 뒤로 이동한다는 기존 브랜치 정책을 유지했습니다. 따라서 이전 `feat/oos` 테스트 DB의 recovery log 번호와 호환되지 않으며 테스트 DB를 다시 만들어야 합니다.

같은 파일의 `RVOOS_NOTIFY_VACUUM` 주석은 과거 특정 번호 134에 고정된다고 적혀 있어 현재 정책과 모순됐습니다. 특정 번호를 제거하고 “OOS block의 reserved slot”이라고 수정하여 이후 `develop` 병합에서도 주석이 즉시 낡지 않도록 했습니다.

관련 위치: `src/transaction/recovery.h:191`, `src/transaction/recovery.h:200`, `src/transaction/recovery.h:214`

## 5. 테스트가 발견한 추가 의미 충돌

대상:

- `src/parser/parser_message.h`
- `msg/en_US.utf8/cubrid.msg`
- `msg/ko_KR.utf8/cubrid.msg`

첫 전체 테스트에서 `test_oos_sql_storage`의 `OosSqlStorage.ForceOutlineRejectsUnsupportedAttributes`가 실패했습니다. STORAGE 오류를 기대했지만 다음 UUID 오류가 반환됐습니다.

```text
Undefined argument. UUID only supports UUIDv4, or UUIDv7; the version argument cannot be NULL.
```

조사 결과 자동 병합된 tree에는 다음 중복이 있었습니다.

```text
338  OOS CLASS/SHARED storage option 오류
339  OOS FORCE_OUTLINE type 오류
338  develop UUID invalid argument 오류
```

텍스트 conflict marker가 없더라도 같은 message set의 ID가 중복되어 runtime lookup이 UUID 문구를 반환한 것입니다. 사용자 원칙에 따라 `develop` UUID 오류를 먼저 유지하고 OOS 메시지를 아래로 이동했습니다.

```text
338  UUID invalid argument                         develop
339  CLASS/SHARED storage option 오류              OOS
340  FORCE_OUTLINE variable normal attribute 오류  OOS
```

관련 위치: `src/parser/parser_message.h:525`, `msg/en_US.utf8/cubrid.msg:2005`, `msg/ko_KR.utf8/cubrid.msg:2004`

## 6. 사용자 검토 기록

모든 텍스트 conflict chunk와 테스트가 발견한 의미 충돌에 대해 수정 전에 원인과 제안 해법을 제시하고 승인을 받았습니다.

| 검토 단위 | 사용자 결정 |
|---|---|
| Chunk 1, 영어 오류 메시지 | `develop`을 우선하고 OOS 오류는 항상 아래로 이동 |
| Chunk 2, 한국어 오류 메시지 | 같은 원칙을 항상 적용 |
| Chunk 3, 오류 코드 정의 | 승인 |
| Chunk 4, heap buffer/flag 결합 | 승인 |
| Chunk 5, recovery handler 배열 | 승인 |
| Chunk 6, recovery enum 및 주석 | 승인 |
| 추가 의미 충돌, parser message ID | 승인 |

승인 전에 해당 chunk를 수정하지 않았으며, 승인된 결정과 다른 해법은 적용하지 않았습니다.

## 7. 검증

로컬 개인 빌드 도구의 `debug_gcc` preset에서 빌드·설치와 전체 configured CTest를 수행했습니다.

| 검증 | 결과 |
|---|---|
| 미해결 Git index entry | 없음 |
| 대상 파일 conflict marker | 없음 |
| 첫 compile | 성공 |
| 첫 install 시도 | 다른 OOS CTest가 runtime lock을 보유해 안전하게 연기됨; 프로세스를 중단하지 않고 종료 후 재시도 |
| install 재시도 | 성공 |
| 첫 CTest | 24/25 성공, parser message ID 의미 충돌 발견 |
| 의미 충돌 수정 후 rebuild/install | 성공 |
| 최종 CTest | 25/25 성공 |
| 최종 전체 테스트 시간 | 104.63초 |

최종 테스트에는 OOS CRUD, multi-chunk, bestspace, SERVER_MODE, mock/real vacuum, SQL DDL·UPDATE·DELETE·transaction, OOS+bigone 거부, storage option, SHOW HEAP OOS, record flag 분리 및 TDE gate가 포함됐습니다.

Debug build의 log 초기화는 `rv_check_rvfuns()`를 호출합니다(`src/transaction/log_manager.c:1116`). 여러 SERVER_MODE 테스트가 정상 부팅하고 전체 테스트가 통과했으므로 enum과 `RV_fun[]`의 위치 불일치는 발생하지 않았습니다.

Message set 중복 검사에서는 이번 자동 병합으로 생긴 semantic ID 337/338 충돌이 제거됐습니다. 325 중복 한 건은 merge base와 양쪽 부모 모두에 이미 존재하므로 이번 병합 범위에서 수정하지 않았습니다.

## 8. 커밋 위생과 보존 사항

개인 pre-commit hook은 staged C/C++ 파일 전체를 자동 포맷합니다. 이번 merge에는 `develop`에서 들어온 대규모 engine 변경이 포함되어 있으므로 hook 실행 시 충돌 해결과 무관한 변경이 생길 수 있습니다. 빌드와 테스트를 통과한 merge tree를 그대로 커밋하기 위해 이 merge commit에서만 `LEFTHOOK=0`을 사용했습니다.

`develop`의 `src/storage/btree_load.c`에는 기존 trailing whitespace 한 건이 포함되어 있습니다. 사용자의 “`develop` 우선” 원칙과 충돌 해결 범위를 지키기 위해 별도 수정하지 않았습니다.

작업 전부터 존재한 다음 내용은 merge commit에 포함하지 않았습니다.

- `cubrid-cci` 및 `cubrid-jdbc` 서브모듈의 로컬 unstaged 상태
- 개인용 미추적 설정, 디버깅 파일, `justfile`, prompt 문서

원격 push는 수행하지 않았습니다.

## 9. 최종 상태

merge commit `dee68b1f46d38705d1d1068547884f68570a818f`은 다음 두 커밋을 부모로 가집니다.

1. `07fef9d48b4776e60c42e8afa25b9f21c54b8226` — 병합 전 `feat/oos`
2. `af56432c507de2ac9b7b56730297d69259430d63` — 충돌을 발생시킨 `origin/develop` snapshot

`af56432c5`는 merge commit의 조상이므로 요청된 병합은 완료됐습니다. 소스 작업 트리에는 사용자의 기존 unstaged·untracked 파일만 남아 있습니다.
