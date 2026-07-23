# [CBRD-26973] OOS 레코드 플래그와 MVCC 플래그 분리

- JIRA: http://jira.cubrid.org/browse/CBRD-26973
- Source commit: `7dce09935`
- Target branch: `feat/oos`

## Purpose

힙 레코드의 첫 번째 representation word에는 MVCC 생명주기 정보와 OOS 존재 여부가 함께 저장된다. 기존 구현은 이 5비트 영역 전체를 `MVCC flag`로 표현하여, MVCC와 무관한 OOS 메타데이터까지 MVCC 개념에 포함시키고 있었다.

이번 변경은 디스크 포맷과 비트값을 유지하면서 이름과 접근 경계를 다음과 같이 분리한다.

| 구분 | AS-IS | TO-BE |
|---|---|---|
| 전체 5비트 영역 | `OR_MVCC_FLAG_MASK` (`0x1f`) | `OR_RECORD_FLAG_MASK` (`0x1f`) |
| MVCC 생명주기 비트 | 헤더 크기 lookup용 `0x07` 마스크로만 구분 | `OR_RECORD_MVCC_FLAG_MASK` (`0x07`)로 하위 3비트 경계를 명시 |
| OOS 요약 비트 | `OR_MVCC_FLAG_HAS_OOS` | `OR_RECORD_FLAG_HAS_OOS` |
| 첫 word 내 위치 | `OR_MVCC_FLAG_SHIFT_BITS` | `OR_RECORD_FLAG_SHIFT_BITS` |
| 전체 플래그 접근 | `OR_GET_MVCC_FLAG` | `OR_GET_RECORD_FLAGS` |
| MVCC 플래그 접근 | 별도 경계 없음 | `OR_GET_MVCC_FLAGS` |

`OR_RECORD_FLAG_HAS_OOS`의 값은 기존과 동일한 `0x08`이며, 첫 representation word에서의 위치도 24비트 시프트를 그대로 사용한다. 따라서 기존 레코드와 WAL의 바이너리 호환성에는 변화가 없다.

## Implementation

### 1. 레코드 플래그 네이밍과 접근자 분리

`object_representation_constants.h`에서 전체 레코드 플래그 영역과 MVCC 전용 영역을 구분했다.

- `OR_RECORD_FLAG_MASK`: 첫 representation word의 전체 5비트 레코드 플래그 영역
- `OR_RECORD_MVCC_FLAG_MASK`: INSID, DELID, PREV_VERSION_LSA에 대응하는 하위 3비트
- `OR_RECORD_FLAG_SHIFT_BITS`: 기존과 동일한 24비트 위치
- `OR_RECORD_FLAG_MASK_IN_WORD`: 첫 word의 24~28번 비트에 위치한 record flag 영역 마스크
- `OR_RECORD_FLAG_HAS_OOS`: 기존과 동일한 `0x08` OOS 요약 비트

전체 5비트 mask에는 OOS bit와 reserved bit(`0x10`)가 포함되지만, MVCC 생명주기 연산과 헤더 크기 lookup에는 하위 3비트만 전달한다.

`object_representation.h`에는 용도별 접근자를 추가했다.

- `OR_GET_RECORD_FLAGS`: MVCC와 OOS를 포함한 전체 레코드 플래그 반환
- `OR_GET_MVCC_FLAGS`: 전체 플래그 중 MVCC 생명주기 비트만 반환
- `OR_RECORD_HAS_OOS`: 레코드 헤더의 OOS 요약 비트 확인
- `OR_GET_RECORD_REPID_AND_FLAGS`: representation id, record flags, offset/bound bits가 포함된 첫 representation word 원문 반환

기존의 MVCC 이름을 가진 전체 플래그 접근자 및 별칭은 제거했다. 변수 offset table의 개별 OOS 항목을 나타내는 `OR_VAR_BIT_OOS`는 레코드 단위 요약 비트와 역할이 다르므로 변경하지 않았다.

### 2. 직렬화 및 역직렬화 경계 정리

representation id와 플래그 word를 읽고 쓰는 함수를 `or_get_record_repid_and_flags`, `or_set_record_repid_and_flags`로 변경했다. 전체 플래그를 보존해야 하는 경로는 record flag를 사용하고, MVCC 헤더 크기 계산이나 MVCC 필드 유효성 판단에는 반드시 하위 3비트 마스크를 적용했다.

적용 범위는 다음과 같다.

- server/client object representation 직렬화·역직렬화와 class/object 변환
- heap insert, update, delete, overflow/relocation 및 recovery
- vacuum, OOS vacuum, OOS record rebuild와 OOS 요약 비트 검사
- log applier
- loaddb와 catalog class 변환
- OOS 테스트용 레코드 생성 코드

### 3. MVCC 연산에서 OOS 비트 보존

`MVCC_REC_HEADER.mvcc_flag`는 구조체 배치를 변경하지 않고 기존 필드명을 유지하되, 실제로는 전체 레코드 플래그를 담는다는 주석을 추가했다.

- `MVCC_IS_ANY_FLAG_SET`는 MVCC 하위 3비트만 검사한다.
- `MVCC_CLEAR_ALL_FLAG_BITS`는 MVCC 하위 3비트만 지우고 OOS 비트는 보존한다.
- `RECORD_HEADER_HAS_OOS`는 구조체 헤더에서 OOS 요약 비트를 명시적으로 검사한다.

이로써 OOS 비트가 설정된 레코드를 MVCC 생명주기 플래그가 설정된 레코드로 오인하거나, MVCC 플래그 초기화 과정에서 OOS 비트를 함께 제거하는 문제를 방지한다.

### 4. 디스크 포맷 불변성

변경 전후의 비트 배치는 동일하다.

```text
31            29 28       24 23                         0
+---------------+-----------+----------------------------+
| offset/bound  | rec flags | representation id          |
+---------------+-----------+----------------------------+
                  |||||
                  ||||+-- INSID          (0x01)
                  |||+--- DELID          (0x02)
                  ||+---- PREV_VERSION   (0x04)
                  |+----- HAS_OOS        (0x08)
                  +------ reserved       (0x10)
```

상수와 내부 API 이름을 역할에 맞게 변경하고, MVCC 전용 연산에는 하위 3비트 마스크를 적용했다. 플래그 값, 시프트, 헤더 필드 순서, 헤더 크기와 WAL 데이터 표현은 변경하지 않았다.

바이너리 호환성 근거는 다음과 같다.

| 항목 | 변경 전 | 변경 후 | 결과 |
|---|---:|---:|---|
| 전체 record flag mask | `0x1f` | `0x1f` | 동일 |
| MVCC header-size mask | `0x07` | `0x07` | 동일 |
| OOS summary bit | `0x08` | `0x08` | 동일 |
| record flag shift | 24 | 24 | 동일 |
| representation id mask | `0x00ffffff` | `0x00ffffff` | 동일 |

`MVCC_REC_HEADER`는 필드 순서와 크기를 유지하고 `mvcc_flag` 필드명도 호환성을 위해 그대로 두었다. 이 변경에는 로그 레코드 구조나 recovery data payload를 추가·삭제·재배열하는 수정이 없다.

## Remarks

### Test Plan

- Debug GCC 전체 빌드 및 설치 성공
- Release GCC 전체 빌드 및 설치 성공
- 신규 `test_oos_record_flags`를 Debug/Release에서 각각 실행하여 통과
  - 전체 record flags와 하위 3비트 MVCC flags가 각각 올바르게 추출되는지 검증
  - OOS summary bit가 독립적으로 검출되는지 검증
  - `MVCC_CLEAR_ALL_FLAG_BITS` 이후에도 OOS bit가 보존되는지 검증
- stale local DB fixture를 격리한 clean retry에서 Debug OOS 테스트 모음 25개 전체 통과 (`0 failed`, 47.93초)
  - DB setup/cleanup fixture와 OOS CRUD, vacuum, recovery 및 SQL 테스트 포함
  - DB fixture에 의존하지 않는 `test_oos_record_flags`, `test_byte_span_writer`, `test_oos_tde_gate` 포함

### Compatibility

- 온디스크 레코드 포맷 변경 없음
- WAL 포맷 변경 없음
- `OR_RECORD_FLAG_HAS_OOS` 값 `0x08` 유지
- `OR_VAR_BIT_OOS` 값과 의미 유지
- 외부 공개 API 변경 없음

### Review Focus

- 전체 레코드 플래그가 필요한 경로와 MVCC 하위 3비트만 필요한 경로가 올바르게 구분되었는지
- MVCC 헤더 크기 lookup이 항상 `OR_RECORD_MVCC_FLAG_MASK`를 적용하는지
- insert/update/delete/vacuum/recovery에서 OOS 비트가 손실되지 않는지
- 제거된 내부 별칭에 누락된 호출부가 없는지
