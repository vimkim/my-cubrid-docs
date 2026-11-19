https://jira.cubrid.org/browse/CBRD-28062

## Purpose

- OOS로 값을 보내기 시작하는 임계값을 서버 설정으로 정할 수 있게 합니다.
- 지금 기본 임계값에서는 develop에서 heap에 남던 4~16KB 행도 OOS로 옮겨집니다. 그래서 이 행들을 전체로 읽으면 CPU 명령어를 2.8~69.5% 더 씁니다(CBRD-27788 측정). 사용자는 이 동작을 바꿀 수 없습니다.
- AS-IS: 임계값은 한 페이지에 행 4개가 들어가는 고정값입니다(16KiB 페이지에서 4,060B).
- TO-BE: `oos_trigger_threshold` 로 임계값을 바이트 단위로 정합니다. 기본값 `0` 은 지금과 같은 자동 계산입니다.

## Implementation

- 서버 파라미터 `oos_trigger_threshold` 를 추가합니다. 서버 재시작이 필요한 static 파라미터이고, `4K` 같은 크기 단위를 받습니다.
  - `prm_Def[]` 의 맨 끝에 추가해서, PL 서버(`SysParam.java`)가 쓰는 기존 파라미터 번호를 바꾸지 않습니다.
- `heap_oos_inline_target_size()` 는 값이 `0` 이 아니면 그 값을 반환합니다. INSERT·UPDATE의 행 배치 계산과, 클라이언트가 만든 레코드를 다시 배치할지 정하는 판정이 둘 다 이 함수를 씁니다. 그래서 두 곳이 같은 임계값을 씁니다.
- `heap_manager_initialize()` 는 `0` 이 아닌 값이 25B(OOS stub 24B + 1)보다 작거나 `heap_Maxslotted_reclength` 보다 크면 `ER_PRM_BAD_VALUE` 로 시작을 거부합니다. 상한은 16KiB 페이지에서 16,236B, 4KiB 페이지에서 3,948B입니다.
  - 상한은 overflow 거부 판정과 같은 경계입니다. 그래서 상한에서도 한 페이지를 넘는 행은 큰 값부터 OOS로 보내고, 거부되지 않습니다.
- 레코드 형식과 로그 형식은 바꾸지 않습니다. 저장된 값은 행의 OOS flag로 읽으므로, 설정을 바꾼 뒤에도 그대로 읽힙니다. 새 값은 이후의 INSERT와 UPDATE에만 적용됩니다.

## Remarks

- 기본값은 바꾸지 않습니다. 값별 성능 측정(sweep) 뒤에 별도로 정합니다.
- 컬럼 `STORAGE` 정책(`FORCE_OUTLINE`, `PREFER_INLINE`, `FORCE_INLINE`)과 overflow 거부 판정은 임계값과 관계없이 그대로 적용됩니다. 테스트는 정책을 7,500B에서, overflow 거부를 상한에서 확인합니다.
- 추가한 테스트:
  - `test_oos_trigger_threshold`: 4KiB·16KiB DB에서 경계값 수락, 범위 밖 값과 잘못된 값의 시작 거부, `SET SYSTEM PARAMETERS` 거부.
  - `test_oos_sql_storage` 의 `ConfiguredThreshold*` 3개: 설정에 따른 배치 변화, UPDATE 재배치(양방향), 상한에서의 동작, `STORAGE` 정책, 경계 비교.
- 검증: `feature/oos-merge` `e262e79fab` 위에서 debug 빌드 ctest 67개 모두 통과.
- HA와 crash recovery는 따로 실행하지 않았습니다. 코드상 replica는 master의 레코드를 다시 배치하지 않으므로 master의 설정을 따릅니다.
