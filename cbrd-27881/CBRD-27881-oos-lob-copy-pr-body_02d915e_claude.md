https://jira.cubrid.org/browse/CBRD-27884

## Purpose

- 상위 작업 CBRD-27881은 `feature/oos-merge`의 OOS 코드에서 정리할 부분을 찾아, 동작을 바꾸지 않는 작은 PR로 나누어 정리하는 작업입니다.
- 이 PR은 `heap_file.c`에서 중복된 LOB 복사 코드를 하나로 합칩니다. 동작은 바뀌지 않습니다.
- AS-IS: BLOB/CLOB 값이 가리키는 외부 LOB 파일(ELO)을 복사하는 약 40줄의 코드가 `heap_attrinfo_transform_variable_to_disk`와 `heap_attrinfo_dbvalue_to_recdes`에 똑같이 들어 있습니다. 두 번째 복사본은 OOS 병합 준비 작업(CBRD-26835)에서 첫 번째를 복사해 만들었습니다.
- TO-BE: 복사 코드는 `heap_attrvalue_copy_lob` 한 곳에만 있고, 두 함수가 이 함수를 부릅니다.

## Implementation

- 새 static 함수 `heap_attrvalue_copy_lob`는 원래 순서 그대로 다음을 수행합니다: 클래스 이름 조회, heap 파일 ID 조회, LOB 경로 prefix 생성, `db_elo_copy_with_prefix` 호출, 메타데이터 복원, `HEAP_WRITTEN_LOB_ATTRVALUE` 표시.
- 두 호출부는 기존 조건문, `assert`, ELO가 없을 때의 `return S_SUCCESS`를 그대로 둡니다. helper가 실패하면 `S_ERROR`를 반환합니다.
- 각 오류 경로에서 해제하는 메모리와, 상태를 바꾸는 시점은 원래 코드와 같습니다.

## Remarks

- 변경 규모는 `src/storage/heap_file.c` 한 파일, 64줄 추가, 75줄 삭제입니다.
- `UNIT_TEST_OOS=ON` debug 빌드에서 OOS 관련 ctest 44개가 변경 전후 모두 통과했습니다. `OosSqlDeferredWrite.LobPreparationPreservesSourceAndDestinationValues`를 gdb로 실행해, 두 호출부가 모두 새 helper를 거치는 것을 확인했습니다.
- 두 원본 블록과 helper 본문을 token 단위로 비교했습니다. 클래스 OID 표현과 반환 코드만 다릅니다.
- 진행 중인 #8350은 이 helper와 같은 위치에 함수를 추가합니다. 나중에 병합되는 PR에서 두 블록을 모두 남기는 단순한 충돌이 하나 생깁니다. #8299와는 충돌하지 않습니다.
- 리뷰 중 기존 동작 하나를 발견했습니다. `heap_attrinfo_transform_variable_to_disk`에서 BLOB/CLOB 값의 ELO가 NULL이면, 남은 컬럼을 쓰지 않고 함수가 `S_SUCCESS`로 끝납니다. 이 PR은 그 동작을 바꾸지 않았으며, 별도 확인이 필요합니다.
