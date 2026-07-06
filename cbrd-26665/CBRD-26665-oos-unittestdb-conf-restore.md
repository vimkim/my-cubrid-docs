# CBRD-26665 OOS unittestdb Config Restore

https://jira.cubrid.org/browse/CBRD-26665

## Purpose

CBRD-26665 는 OOS unit test 가 전용 데이터베이스 `unittestdb` 를 자동으로 만들고 CI 에서 실행되도록 한 작업이다. 이 PR 은 그 fixture 가 설치된 `cubrid.conf` 를 변경한 뒤 원래 상태로 되돌리지 않아, 뒤이어 실행되는 shell test 의 설정이 잘못된 DB 섹션에 들어가는 문제를 고친다.

- AS-IS: `oos_setup_db` 가 `cubrid.conf` 끝에 `[@unittestdb]` 와 `vacuum_log_block_pages=4` 를 남겨, 이후 CTP shell helper 가 EOF 에 붙이는 설정이 전역 설정이 아니라 `unittestdb` 전용 설정처럼 해석될 수 있었다.
- TO-BE: `unittestdb` 생성 시점에만 임시 섹션을 넣고, `createdb` 성공/실패와 무관하게 setup 종료 전에 원본 `cubrid.conf` 를 복원한다. cleanup 은 남아 있을 수 있는 fixture 섹션도 방어적으로 제거한다.

`vacuum_log_block_pages=4` 는 real-vacuum OOS test 에 필요하다. 이 값은 `createdb` 시점에 DB 안에 고정되므로, 섹션을 추가하는 순서는 유지해야 한다. 다만 그 설정이 다른 CI 단계에 남아 있으면 `supplemental_log`, `tde_keys_file_path`, `create_table_reuseoid`, query cache, regexp, string compression 계열 shell test 설정이 무시될 수 있다.

## Implementation

- `unit_tests/oos/CMakeLists.txt` 의 inline `bash -c` fixture 를 `unit_tests/oos/scripts/setup_unittestdb.sh` 와 `unit_tests/oos/scripts/cleanup_unittestdb.sh` 호출로 바꿨다. CMake quoting 안에 있던 설정 변경 로직을 shell script 로 옮겨 실패 처리와 cleanup 을 분리했다.
- `setup_unittestdb.sh` 는 `cubrid.conf` 에 남아 있는 OOS fixture 블록을 먼저 제거한 뒤, `unittestdb` 가 없을 때만 원본을 백업하고 marker-owned 섹션을 임시로 추가한다. `trap` 으로 setup 종료 시 항상 백업을 복원하므로 `cubrid createdb` 가 실패해도 설치 설정은 원래 상태로 돌아간다.
- `cleanup_unittestdb.sh` 는 `unittestdb` server stop 과 deletedb 를 기존처럼 수행한 뒤, `cubrid.conf` 에 남은 fixture 설정을 다시 제거한다. cleanup 이 setup 복원의 주 경로는 아니며, 이전 실패 run 또는 수동 중단의 잔여물을 지우는 방어선이다.
- `oos_unittestdb_common.sh` 는 DB 존재 확인, marker-owned block 제거, legacy exact-shape block 제거, fixture block append 를 공통 함수로 제공한다.

cleanup 은 사용자가 직접 작성한 일반 `[@unittestdb]` 섹션을 지우지 않는다. 새 fixture 는 `# BEGIN OOS unittestdb fixture` 와 `# END OOS unittestdb fixture` marker 로 소유권을 표시한다. 과거 fixture 가 남긴 legacy block 은 파일 끝의 정확한 두 줄, 즉 `[@unittestdb]` 와 `vacuum_log_block_pages=4` 조합만 제거한다.

## Remarks

### Test Plan

- Shell syntax: 새 script 3개에 대해 `bash -n` 을 실행했다.
- Failure path: disposable fake CUBRID 환경에서 `createdb` 실패를 주입하고, `cubrid.conf` 백업이 복원되며 임시 backup 파일이 남지 않는 것을 확인했다.
- Fixture E2E: `ctest --test-dir build_preset_release_gcc -R "oos_setup_db|test_oos_real_vacuum_server|oos_cleanup_db" --output-on-failure --verbose` 를 실행했고, setup/real-vacuum/cleanup 3개 test 가 모두 통과했다. `test_oos_real_vacuum_server` 내부 10개 case 도 모두 통과했다.
- Post-check: fixture 실행 뒤 `cubrid.conf` 에 `unittestdb`, `OOS unittestdb fixture`, `vacuum_log_block_pages=4` 문자열이 남지 않는 것을 확인했다. `databases.txt` 에도 `unittestdb` entry 가 남지 않았다.
- Shell representative: compactdb `bug_xdbms22` shell case 를 실행했고 1개 case 가 성공했다. 이 case 는 `create_table_reuseoid` 설정이 잘못된 섹션에 붙는 회귀를 확인하기 좋은 대표 예이다.

### Review Notes

- 리뷰 시 `setup_unittestdb.sh` 의 `trap restore_conf EXIT` 위치를 먼저 보면 된다. 이 PR 의 핵심은 cleanup 단계까지 기다리지 않고 setup 이 끝나는 즉시 설치 설정을 원복하는 것이다.
- legacy block 제거는 일부러 좁게 잡았다. 추가 사용자 설정이 들어 있는 `[@unittestdb]` 섹션은 보존한다.
- 이 PR 은 OOS storage format, vacuum 동작, OOS read/write 경로를 바꾸지 않는다. 영향 범위는 OOS CTest fixture 의 DB 준비와 cleanup 이다.
