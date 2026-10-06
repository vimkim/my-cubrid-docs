https://jira.cubrid.org/browse/CBRD-27089

## Purpose

OOS는 큰 컬럼 값을 행 밖에 저장하고, 행에는 값을 찾을 참조 정보만 남기는 방식입니다. 행과 OOS 값은 같은 heap이 소유해야 vacuum이 함께 정리할 수 있습니다.

- AS-IS: 파티션 선택 전에 OOS 값을 root heap에 기록하여, child heap에 저장된 행과 값의 소유자가 달라집니다.
- TO-BE: 목적지 heap을 정한 뒤 그 heap의 OOS 파일에 값을 기록합니다.

## Implementation

- `heap_pending_record`가 처음 만든 행 버퍼(`RECDES`)와 OOS 대상 값의 직렬화 바이트를 함께 소유합니다. 행을 버리면 두 메모리도 함께 정리됩니다.
- `heap_oos_value_ref`는 메모리 참조와 디스크 참조를 구분하며, 같은 `length()`·`read_into()` 인터페이스로 값을 읽습니다. 파티션 선택과 인덱스 호출 인터페이스는 유지합니다.
- workspace에서 받은 행은 파티션 결정 후 OOS 변환을 준비합니다. 목적지가 정해지면 OOS 값을 기록하고 기존 24바이트 stub만 실제 OID·길이·identity stamp로 덮어씁니다. 이 단계에서는 행 버퍼를 다시 만들거나 길이·컬럼 위치를 바꾸지 않습니다.
- SQL INSERT·UPDATE·파티션 이동, 중복 키 검사, client row, loader, 재분배에 적용합니다. 복제 apply는 OOS item과 소유 행을 같은 롤백 단위로 처리합니다.
- 메모리 참조는 서버에서 준비한 임시 레코드에서만 허용하고, 저장·전송 전에 임시 상태를 차단합니다. 저장 형식과 통신 형식은 유지합니다.

## Remarks

- 기존 직렬화·컬럼 읽기·최종 저장 함수를 재사용합니다. loader는 행 단위 소유 객체를 큐에 넣고, 행과 OOS 값의 합산 크기로 batch를 비웁니다. 공유 값 목록의 위치를 기억했다가 되돌리는 정리 코드는 제거했습니다.
- server loaddb의 root 입력은 파티션으로 배치하며, child 직접 입력은 범위를 검증합니다. 잘못된 child 입력을 허용하던 테스트의 기대값은 수정이 필요합니다.
- Debug 빌드와 CTest 35/35 통과. 메모리·디스크 값 일치, 동일 RECDES의 stub만 변경, workspace INSERT·파티션 이동과 목적지 소유권, 중복 키 검사, 실패 롤백, 복제 apply를 검증했습니다.
- 실제 server loaddb에서도 600행 batch, 9MiB 단일 행, 800행 파티션 배치, 잘못된 child 입력 거부 후 다음 load 성공을 확인했습니다.
- 전체 SQL·shell·medium 회귀 CI 결과와 PR #7925와의 통합 실행 결과는 아직 확인하지 않았습니다.
