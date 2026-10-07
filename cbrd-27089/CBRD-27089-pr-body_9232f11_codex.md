> Status updated 2026-10-07: Historical PR body at 9232f11; retained as publication evidence.
> Current entry point: [CBRD-27089](README.md). Historical evidence below is preserved.

https://jira.cubrid.org/browse/CBRD-27089

## Purpose

OOS는 큰 컬럼 값을 행 밖의 별도 파일에 저장하고, 행에는 그 값을 찾을 참조 정보를 남기는 방식입니다.
행과 그 OOS 값은 같은 heap이 소유해야, 행을 정리하는 vacuum도 해당 heap의 OOS 파일에서 값을 정리할 수 있습니다.

- AS-IS: 목적지 파티션을 고르기 전에 OOS 값을 root heap에 기록하여, 행은 child heap에 있고 OOS 값은 root에 남습니다. SELECT는 성공해도 vacuum에서 정리 실패·공간 누수가 발생하며, 불변식 검사 계측이 있는 빌드에서는 서버가 중단됩니다.
- TO-BE: 행의 값을 먼저 준비하고 목적지를 결정한 뒤, 그 heap의 OOS 파일에 값을 기록하고 heap record를 완성합니다.

## Implementation

```text
prepare() → 목적지 heap 결정 → finalize(destination) → heap/index 반영
```

- `heap_prepared_row::prepare()`는 모든 컬럼의 직렬화된 바이트를 소유하고 OOS 대상과 행 배치를 정합니다. 새 OOS chain은 만들지 않습니다.
- 파티션 선택과 중복 키 검사는 준비된 값에서 필요한 컬럼을 읽습니다. 기존 파티션 식 평가 로직을 사용합니다.
- `finalize()`는 목적지의 OOS 파일에 값을 기록하고, 반환된 OID·길이·identity stamp로 행 안의 참조 정보인 stub을 채웁니다. 실제 heap 저장과 실패 시 롤백은 호출자가 담당합니다.
- SQL INSERT·UPDATE·파티션 이동, client row, loader, 재분배 경로에 적용합니다. 비파티션 행도 같은 준비 객체를 사용하며, 복제 apply는 OOS item과 소유 행을 한 롤백 단위로 묶습니다.
- 행 전체를 소유하여 입력값의 수명과 inline/OOS 여부를 호출자가 각각 관리하지 않게 합니다. 준비 객체는 이동 가능하고 복사는 금지됩니다.

## Remarks

- 두 번 변환하던 PR #7600을 대체합니다. `DB_VALUE`를 유지하거나 OOS 값만 별도 보관하는 대안도 가능하지만, 이 PR은 여러 입력 경로의 값 보관과 접근을 행 단위로 통일했습니다.
- server loaddb는 root 입력을 파티션으로 배치하고, child 직접 입력은 범위를 검증합니다. 잘못된 파티션 입력을 허용하던 테스트의 기대값 변경이 필요합니다.
- 추가 검토 사항: loader의 파티션 BU lock·행별 통계, 복제 오류의 롤백 범위, fixed 영역 padding을 포함한 OOS 경계 판정, 사용되지 않는 MVCC 할당 재평가 경로 차단입니다.
- 저장·통신 형식은 유지합니다. 값 보관 시간이 늘며, 과거 `512b361a7` 측정에서는 loader server peak 메모리가 약 7~8 MiB 증가했습니다.
- 설명 기준은 `9232f111a7e7b6c71dbfa451db2812ae14766041`입니다. 과거 커밋의 CTest·회귀 검증 결과와 현재 head의 검증 범위를 상세 문서에서 구분합니다.
- 자세한 설명: [준비된 행의 구조·설계 대안·실패 처리·검증 근거](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27089/CBRD-27089-prepared-row-explained_9232f11_codex.md)
