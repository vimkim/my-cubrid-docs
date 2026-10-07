https://jira.cubrid.org/browse/CBRD-27089

## Purpose

OOS는 큰 컬럼 값을 행 밖에 저장하는 방식입니다. 행과 OOS 값은 같은 heap(행 저장 파일)이 소유해야 vacuum(오래된 값 정리)이 함께 처리할 수 있습니다.

- AS-IS: 파티션 선택 전에 OOS 값을 root heap에 기록하여, child heap에 저장된 행과 값의 소유자가 달라집니다.
- TO-BE: 목적지 heap을 정한 뒤 그 heap의 OOS 파일에 값을 기록합니다.

## Implementation

- `heap_pending_record`가 처음 만든 작은 행 버퍼와 저장할 값의 직렬화 바이트(payload)를 함께 소유합니다. 읽기 함수에는 이 소유 객체(owner)를 빌려 전달하고, 호출자가 사용이 끝날 때까지 살려 둡니다.
- 임시 24바이트 stub(행 안의 참조 정보)은 메모리 주소 대신 owner 안의 payload 번호와 길이를 담습니다. `REC_OOS_PENDING`을 제거하고 다른 record type은 추가하지 않습니다. 공용 `RECDES` 배치도 유지합니다.
- `heap_oos_value_ref`로 메모리·디스크 값을 같은 방식으로 읽습니다. 메모리 참조는 owner의 준비 상태·행 버퍼·번호·길이를 검증해야 읽을 수 있고, 미완성 참조는 일반 행 저장과 fetch 응답에서 차단합니다.
- 목적지를 정한 뒤 보관한 payload를 OOS에 기록하고 기존 stub만 실제 OID·길이·identity stamp로 덮어씁니다. 이 단계에서 행 버퍼를 다시 만들지 않으며, 저장 형식과 통신 형식은 유지합니다.
- finalizer는 값별 payload·삽입 결과·stub 위치를 묶고, 검증한 stub을 다시 찾지 않고 해석합니다. 전체 삽입이 성공한 뒤에만 stub을 바꿉니다.
- INSERT와 이동 없는 UPDATE는 목적지 선택 뒤 하나의 locator 함수에서 입력 변환과 finalization을 처리합니다. 파티션 이동 UPDATE는 owner를 목적지 INSERT에 전달합니다.
- SQL INSERT·UPDATE·중복 키 탐색, client row, loader, 재분배를 처리하며, 중복 탐색만으로 OOS를 기록하지 않습니다. loader는 행별 owner를 큐에 넣고 행·payload의 합산 크기로 batch를 비웁니다. 복제 apply는 OOS 값과 소유 행을 같은 롤백 단위로 처리합니다.
- SHOW 진단 4개와 쓰기 검증 36개를 분리했습니다. 쓰기 검증은 `test_oos_sql_deferred_write.cpp`로 옮기고 필요한 DB fixture·통계 helper만 공유합니다.

## Remarks

- `4be72fc20`: Debug 빌드·설치, 전체 CTest 36/36 통과(245.43초). 두 SQL 모듈의 40개 GoogleTest도 통과했습니다.
- 테스트 분리 전 `6b53181d3`의 40개 테스트 본문은 그대로 유지됩니다. 단순화 변경의 독립 Standards·Spec 리뷰는 각각 남은 지적 0건입니다.
- `6b53181d3`의 assertions-disabled 경계 검증과 실제 server loaddb 검증은 이전 리비전의 결과입니다. loaddb는 600행 batch·9MiB 단일 행·800행 파티션 배치·잘못된 child 입력 거부 후 다음 load를 검증했습니다. 값 검증은 통과했지만 master의 정상 종료 코드가 1이어서 실행 스크립트도 1로 끝난 점을 별도로 기록했습니다. `4be72fc20`에서는 이 두 검증을 다시 실행하지 않았습니다.
- client copy-area의 서버 변환 비용은 추가되며 전체 성능 영향은 측정하지 않았습니다. 변경 없는 OOS 체인의 재사용은 vacuum 소유권·복제 계약을 함께 바꾸는 CBRD-27230 범위로 남깁니다.
- 최종 리비전의 전체 SQL·shell·medium CI와 PR #7925 통합 검증은 아직 확인하지 않았습니다. 잘못된 child 입력을 허용하던 테스트의 기대값 수정과 medium 순서 차이의 원인 확인도 남아 있습니다.
