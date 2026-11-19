https://jira.cubrid.org/browse/CBRD-28062

## Purpose

- OOS로 값을 보내기 시작하는 임계값을 서버 설정으로 정할 수 있게 합니다.
- 지금 기본 임계값에서는 develop에서 heap에 남던 4~16KB 행도 OOS로 옮겨집니다. 그래서 이 행들을 전체로 읽으면 CPU 명령어를 2.8~69.5% 더 씁니다(CBRD-27788 측정). 사용자는 이 동작을 바꿀 수 없습니다.
- AS-IS: 임계값은 한 페이지에 행 4개가 들어가는 고정값입니다(16KiB 페이지에서 4,060B).
- TO-BE: `oos_trigger_threshold` 로 임계값을 바이트 단위로 정합니다. 기본값 `0` 은 지금과 같은 자동 계산입니다.

## Implementation

- 서버 파라미터 `oos_trigger_threshold` 를 추가합니다. 서버 재시작이 필요한 static 파라미터이고, 값은 바이트 정수입니다. 범위가 바이트 단위로 정확해야 해서 `4K` 같은 크기 단위는 받지 않습니다(`paramdump` 도 정확한 바이트를 출력합니다).
  - `prm_Def[]` 의 맨 끝에 추가해서, PL 서버(`SysParam.java`)가 쓰는 기존 파라미터 번호를 바꾸지 않습니다.
- `heap_oos_inline_target_size()` 는 값이 `0` 이 아니면 사용자 클래스에 그 값을 반환합니다. INSERT·UPDATE의 행 배치 계산과, 클라이언트가 만든 레코드를 다시 배치할지 정하는 판정이 둘 다 이 함수를 쓰므로 두 곳이 같은 임계값을 씁니다.
  - 시스템 클래스(`_db_serial` 등)는 설정과 관계없이 항상 자동 기본값을 씁니다. serial의 NEXT VALUE는 행을 제자리에서 고쳐 씁니다. 임계값을 올리면 OOS로 나갔던 comment가 행 안으로 돌아오면서 행이 커지고, 페이지에 자리가 없으면 갱신이 실패합니다(4KiB 페이지에서 재현). 시스템 클래스를 제외하면 catalog 행의 배치는 이 PR 이전과 같습니다.
- `heap_oos_check_trigger_threshold()` 는 `0` 이 아닌 값이 자동 기본값보다 작거나 `heap_Maxslotted_reclength` 보다 크면 `ER_PRM_BAD_VALUE` 로 시작을 거부합니다. 허용 범위는 4KiB 페이지에서 988~3,948B, 8KiB 페이지에서 2,012~8,044B, 16KiB 페이지에서 4,060~16,236B입니다.
  - 페이지 크기를 안 뒤에 검사합니다(서버 시작, createdb, emergency patch). restoredb는 레코드를 배치하지 않고, 볼륨을 덮어쓴 뒤 실패하면 반쯤 복구된 DB가 남으므로 검사하지 않습니다. 다음 정상 시작에서 검사합니다.
  - 하한: 이 파라미터는 임계값을 올리는 용도입니다. 기본값보다 낮은 값은 측정 근거가 없어 받지 않습니다.
  - 상한: overflow 거부 판정과 같은 경계입니다. 그래서 상한에서도 한 페이지를 넘는 행은 큰 값부터 OOS로 보내고, 거부되지 않습니다.
- 레코드 형식과 로그 형식은 바꾸지 않습니다. 저장된 값은 행의 OOS flag로 읽으므로, 설정을 바꾼 뒤에도 그대로 읽힙니다. 새 값은 이후의 INSERT와 UPDATE에만 적용됩니다.

## Remarks

- 기본값은 바꾸지 않습니다. 값별 성능 측정(sweep) 뒤에 별도로 정합니다.
- 성능 근거: CBRD-27788에서 임계값을 상한으로 고정한 측정용 빌드는 4~16KB 값 전체 읽기 12개 경우가 develop 대비 −0.24%~+0.08%였습니다(명령어 수). 이 PR의 상한 설정과 같은 배치입니다. 이 PR 빌드로 하는 값별 측정은 진행 중이고, 결과는 CBRD-28062에 남깁니다.
- 컬럼 `STORAGE` 정책(`FORCE_OUTLINE`, `PREFER_INLINE`, `FORCE_INLINE`)과 overflow 거부 판정은 임계값과 관계없이 그대로 적용됩니다. 테스트는 정책을 7,500B에서, overflow 거부를 상한에서 확인합니다.
- 추가한 테스트:
  - `test_oos_trigger_threshold`: 4KiB·16KiB DB에서 하한과 상한 경계값의 수락과 거부, 잘못된 값과 `4K` 의 시작 거부, `SET SYSTEM PARAMETERS` 거부.
  - `test_oos_trigger_threshold_system`: 4KiB DB에서 serial의 comment가 OOS로 나간 뒤 임계값을 상한으로 올려도 NEXT VALUE와 checkdb가 성공하는지, 범위 밖 값으로도 restoredb가 백업 이후 커밋까지 복구하는지 확인합니다. 수정 전 코드에서는 첫 번째 확인이 `serial.c:1587` assert로 실패합니다.
  - `test_oos_sql_storage` 의 `ConfiguredThreshold*` 3개: 설정에 따른 배치 변화, UPDATE 재배치(양방향), 상한에서의 동작, `STORAGE` 정책, 경계 비교.
- 검증: debug 빌드 ctest 68개 모두 통과.
- CS 모드 INSERT와 CS 모드 loaddb에서 서버 설정이 적용되는 것을 확인했습니다. 6,000B 값이 기본값(`0`)에서는 OOS로 가고(행 44~52B), 상한에서는 heap에 남습니다(행 6,032~6,040B).
- HA와 crash recovery는 따로 실행하지 않았습니다. 코드상 replica는 master의 레코드를 다시 배치하지 않으므로 master의 설정을 따릅니다.
- 알려진 한계와 별도 이슈: `createdb -r` 은 기존 볼륨을 지운 뒤 범위 검사에 실패할 수 있습니다(CBRD-28268). 리뷰 중 찾은 기존 결함은 CBRD-28266, CBRD-28267, CBRD-28073 댓글로 남겼습니다.
