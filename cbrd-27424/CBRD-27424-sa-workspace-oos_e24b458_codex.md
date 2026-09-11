# CBRD-27424: standalone workspace 쓰기의 OOS 지원

https://jira.cubrid.org/browse/CBRD-27424

## Purpose

OOS (Out-of-row Overflow Storage)는 큰 컬럼 값을 별도 페이지에 저장하는 기능이다. 이 변경은 standalone 객체 적재와 같은 경로를 사용하는 CSQL 쓰기에서 빠져 있던 OOS 변환을 연결한다.

- AS-IS: `loaddb -S`와 CSQL의 workspace 쓰기는 큰 값을 정확히 저장하지만 OOS 변환을 호출하지 않아 값을 행 내부에 둔다.
- TO-BE: 해당 쓰기도 기존 OOS 정책에 따라 큰 값을 분리하고, 원래 값과 객체 참조를 유지한다.

기준 커밋은 `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (`feat/oos`)이며, 변경 커밋은 `e24b458bfea4d49cc763328c055c5c5374694b06`이다. PR #7695의 변경을 이 브랜치에 포함하지 않고 별도로 호환성을 확인했다.

### 재현과 원인

압축 영향을 피하기 위해 고정 난수로 만든 5,000바이트 VARBIT 값을 사용했다. 커밋 후 새 연결에서 정확한 값 일치와 `;oos_stats`의 실제 OOS 레코드 수를 함께 확인했다.

| 쓰기 경로 | 변경 전 OOS 레코드 수 | 변경 후 OOS 레코드 수 | 값 일치 |
|---|---:|---:|---|
| `loaddb -S` | 0 | 1 | 모두 통과 |
| 일반 INSERT, `csql -S` | 1 | 1 | 모두 통과 |
| 일반 INSERT, `csql -C` | 1 | 1 | 모두 통과 |
| `loaddb -C` | 1 | 1 | 모두 통과 |
| CSQL workspace INSERT | 0 | 1 | 모두 통과 |

CSQL은 `-S`만으로 workspace 경로를 선택하지 않는다. `insert_execution_mode=0`으로 해당 경로를 선택하여 별도로 확인했다.

디버거에서 SA loader는 `tf_mem_to_disk`를 한 번 호출했지만 `heap_attrinfo_determine_disk_layout`과 `oos_insert_many`를 호출하지 않았다. 일반 CSQL INSERT는 두 함수를 각각 한 번 호출했다. 문제는 값 손실이나 OOS 정책의 거절이 아니라 변환 호출의 누락이었다.

## Implementation

### 공통 force 경계에서 변환

`src/transaction/locator_sr.c`의 `locator_demote_workspace_record`가 SA workspace 레코드를 읽고 기존 heap attribute 변환기를 호출한다. 새 OOS 선택 정책을 추가하지 않는다.

- `from_workspace` 인자로 workspace 쓰기를 구분한다. INSERT, 예약된 OID를 채우는 UPDATE, 여러 행 UPDATE를 포함한다.
- 실제 파티션과 heap이 결정된 뒤 변환한다. 파티션 이동은 대상 INSERT까지 이 구분을 전달한다.
- 기존 force top operation 안에서 OOS 생성과 heap/index 쓰기를 수행한다. 전체 롤백뿐 아니라 오류를 무시하고 계속하는 적재의 객체별 롤백도 같은 범위에 들어간다.
- 별도 copyarea에 변환 결과를 만들고 성공·실패 경로에서 해제한다. 호출자의 원본 버퍼를 덮어쓰지 않는다.
- OOS 분리가 선택되지 않으면 원본 레코드를 유지한다. 분리되면 workspace에서 정한 CHN (캐시 변경 번호)을 보존한다.
- 이미 변환한 레코드와 클래스 정의는 제외한다. SERVER 모드에서는 새 변환을 수행하지 않는다.
- `LOB_FLAG_EXCLUDE_LOB`로 이미 저장된 외부 BLOB/CLOB를 다시 복사하지 않는다.

`src/transaction/locator_sr.h`에는 호출 경로를 구분하는 기본 인자를 추가했다. 기존 SQL 실행기, CS loader, 복제 경로는 기존 호출 동작을 유지한다.

### 회귀 테스트

`unit_tests/oos/scripts/test_workspace_oos.py`를 `test_oos_workspace_cli`라는 CTest로 등록했다. 설치된 `cubrid`와 `csql`, Python 3가 필요하다. 전용 DB 등록 파일과 16 KiB 페이지의 임시 DB를 만들고 실제 CLI 경로를 실행한다.

테스트는 논리 값뿐 아니라 실제 OOS 조각 수를 확인한다. 성공한 임시 DB는 삭제하며 실패 시 출력과 DB를 남겨 원인을 조사할 수 있다.

## Remarks

### Test Plan

| 검증 | 결과 |
|---|---|
| 변경 전 최소 SA loader 회귀 테스트 | 값 일치는 통과, OOS 수가 0이므로 실패 |
| 변경 전 GCC debug CTest | 27/27 통과 |
| 변경 후 GCC debug 빌드 및 CTest | 28/28 통과, 176.16초 |
| 새 CLI 회귀 테스트 | 12개 시나리오 통과, 62.86초 |
| SA/CS loader 및 일반 CSQL 4개 경로 재실행 | 모두 통과, 17.48초 |
| PR #7695 head에 동일 패치 적용 및 빌드 | 통과 |
| PR #7695 head에서 새 CLI 회귀 테스트 | 12개 시나리오 모두 통과 |
| 코드 표준·스펙 리뷰 및 포맷 검사 | 확인된 코드 결함 없음, 포맷 일치 |

12개 시나리오는 기본 SA loader, CSQL workspace INSERT, 앞뒤 객체 참조, 파티션별 소유권, INSERT 롤백, UPDATE/DELETE 정리, 전체 적재 실패, 무시한 중복 키 이후 적재 계속, 기존 외부 LOB 보존, 저장 정책 및 여러 조각, 파티션 이동, no-logging 적재이다.

저장 정책 검증에는 NULL·빈 값·작은 값, FORCE_OUTLINE, 큰 컬럼 우선 선택, 50,000바이트의 4개 조각 저장을 포함한다. 오류를 무시하는 테스트는 거절된 중복 행의 OOS 조각이 남지 않고 다음 정상 행이 커밋되는지 확인한다.

### 호환성과 범위

[PR #7695](https://github.com/CUBRID/CUBRID/pull/7695)의 `eaf1165bbc76d5f22b6ff34f08ccd8deca0c11b4`에서 동일한 추가·삭제 코드와 동일한 테스트를 별도 빌드 및 새 DB로 실행했다. 이는 빌드와 집중 회귀 검증 결과이며, 해당 PR의 전체 테스트나 CI 결과를 뜻하지 않는다.

이 변경은 OOS 참조의 디스크 형식이나 크기 선택 기준을 바꾸지 않는다. 현재 기준 브랜치의 16바이트 참조와 PR #7695의 identity stamp 변경은 각각 유지했다. no-logging은 성공한 적재와 읽기를 검증했으며, 실패 후 복구나 식별자 유일성을 새로 보장하지 않는다.

기존 외부 LOB 검증은 다른 컬럼을 OOS로 분리하면서 BLOB/CLOB 내용, 파일 이름, 파일 바이트가 롤백·커밋 후 유지되는지 확인한다. LOB locator 자체를 OOS로 분리하는 모든 조합을 검증한 것은 아니다. 새 외부 LOB를 workspace INSERT로 만들 때의 별도 기존 결함은 수정 범위에 포함하지 않았다.

검증은 위 변경 커밋과 동일한 소스 내용으로 수행했다. 이 문서는 로컬 진단 보고서의 공개용 정리이며, 기계별 경로나 개인 빌드 도구에 의존하는 지침을 포함하지 않는다.
