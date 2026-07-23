# CBRD-27093 — DWB 비활성 시 checkpoint 영구 볼륨 동기화 복원

## Purpose

- JIRA: <http://jira.cubrid.org/browse/CBRD-27093>
- 기준 소스 커밋: `85b6b5743d8cd93e56542de1858b4e507e2a5f21`
- 선행 분석: [DWB off checkpoint fsync 누락 분석](./CBRD-27093-dwb-off-checkpoint-fsync-missing.md)

`double_write_buffer_size=0`은 지원되는 설정이지만, 이 상태에서
`dwb_flush_force()`는 DWB가 아무 작업도 하지 않았는데도 `all_sync=true`를
반환했다. 호출자인 `fileio_synchronize_all()`은 이를 영구 볼륨 동기화 완료로
해석하여 자체 볼륨 순회 `fsync`를 생략했다.

| 구분 | AS-IS | TO-BE |
|---|---|---|
| DWB 미생성 | `all_sync=true` | `all_sync=false` |
| `fileio_synchronize_all()` | 영구 볼륨 순회 생략 | 영구 볼륨을 직접 순회하여 동기화 |
| 명시적 checkpoint 실측 | 영구 base 볼륨 sync 0회 | 영구 base 볼륨 sync 4회 |
| DWB 정상 활성 경로 | DWB 완료 후 `true` | 기존과 동일하게 `true` |

AS-IS 재현에서는 DWB 파일이 없고 checkpoint 명령이 성공했으며 active log는
2회 동기화되었지만 영구 base 볼륨 동기화는 0회였다. 따라서 명령 성공이나 로그
동기화만으로 checkpoint의 데이터 볼륨 durability 계약을 보장할 수 없었다.

## Implementation

`src/storage/double_write_buffer.cpp`에서 `all_sync`의 의미를 "DWB 경로가 모든
영구 볼륨의 동기화를 보증함"으로 명확히 했다. 함수 진입 시의 `false`를
유지하고, DWB가 동기화 완료를 보증하는 경로만 `end_all_sync`를 통해 `true`로
설정한다.

다음 세 DWB 비활성 경로는 모두 호출자 fallback이 필요하므로 `false`를 유지한다.

1. 함수 진입 시점부터 DWB가 생성되지 않은 경우
2. flush 진행 중 DWB가 비활성화된 경우
3. null page 추가 중 DWB 비활성화를 감지한 경우

DWB가 활성 상태이고 동기화할 helper block이 없거나 helper block 완료를 기다린
경로는 기존처럼 `true`를 반환한다. 따라서 기본 DWB 활성 구성에는 추가 볼륨
동기화가 발생하지 않는다. 오류 반환 경로의 동작도 변경하지 않았다.

이 계약 수정은 `fileio_synchronize_all()`의 전체 영구 볼륨 순회뿐 아니라
`dwb_synchronize()`의 개별 영구 볼륨 `fsync` fallback도 함께 복원한다. 호출자
코드는 이미 올바른 fallback을 갖고 있으므로 호출자별 수정은 필요하지 않다.

`unit_tests/double_write_buffer/`에 DWB 미생성 상태에서
`dwb_flush_force(NULL, &all_sync)`가 `NO_ERROR`와 `all_sync=false`를 반환하는
Catch2 회귀 테스트를 추가했다. 전용 CMake option으로 단독 빌드할 수 있으며,
전체 `UNIT_TESTS` 구성에도 포함된다.

## Remarks

### Test Plan

단위 테스트는 다음 계약을 검증한다.

1. 테스트 시작 시 DWB가 생성되지 않았음을 확인한다.
2. `all_sync=true`로 초기화한 뒤 `dwb_flush_force()`를 호출한다.
3. 반환값이 `NO_ERROR`이고 `all_sync`가 `false`로 바뀌었는지 확인한다.

통합 시나리오는 syscall 부재/존재를 직접 판별한다.

1. `double_write_buffer_size=0`, 자동 checkpoint 비활성으로 DB를 시작한다.
2. DWB 파일이 생성되지 않았음을 확인하고 100,000행 workload를 적재한다.
3. `strace -f -y -e trace=fsync,fdatasync`를 서버에 attach한다.
4. attach 완료 후 명시적 `;checkpoint`만 실행하고 서버 완료를 기다린다.
5. 정확한 영구 base 볼륨 경로의 성공한 sync가 1회 이상인지 검사한다.
6. active log sync도 1회 이상인지 확인하여 빈 trace/잘못된 attach를 배제한다.

실행 결과:

- Debug 전체 빌드 및 설치: 성공
- `test_double_write_buffer --reporter compact`: 1 case, 3 assertions 통과
- 수정 전 syscall 시나리오: 영구 base 볼륨 0회, active log 2회
- 수정 후 CTP syscall 시나리오: 영구 base 볼륨 4회, active log 3회, OK

syscall 시나리오는 Linux `strace`와 ptrace attach 권한이 필요하다. SQL 결과만으로는
fsync 호출 부재를 판별할 수 없으므로 SQL-only 회귀 테스트는 추가하지 않았다.

이번 변경은 fsync 실패 처리 정책을 바꾸지 않는다. DWB 활성/비활성 공통의 fsync
실패 severity와 서버 지속 여부는 별도 설계 범위다.
